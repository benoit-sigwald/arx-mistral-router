"""Mistral API client with rate-limiting, retries, caching, and usage tracking."""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from .config import RouterConfig
from .rate_limiter import FreeTierRateLimiter
from .sanitization import bound_and_sanitize
from .usage import UsageTracker, get_usage_tracker

logger = logging.getLogger("arx_mistral_router")


class MistralRouterClient:
    """Robust, cached, and rate-limited client for Mistral AI."""

    def __init__(self, config: RouterConfig, usage_tracker: Optional[UsageTracker] = None):
        self.config = config
        self.usage_tracker = usage_tracker or get_usage_tracker(config.monthly_token_budget)
        self.rate_limiter = FreeTierRateLimiter(
            rps_limit=config.rate_limit_rps,
            tpm_limit=config.rate_limit_tpm,
            max_concurrent=config.max_concurrent_requests,
        )
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.request_timeout_seconds, connect=10.0),
                headers={
                    "Authorization": f"Bearer {self.config.mistral_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ARX-Mistral-Router/1.0",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _generate_cache_key(self, model: str, system_prompt: str, user_content: str) -> str:
        h = hashlib.sha256()
        h.update(model.encode("utf-8"))
        h.update(b"::")
        h.update(system_prompt.encode("utf-8"))
        h.update(b"::")
        h.update(user_content.encode("utf-8"))
        return h.hexdigest()

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.config.cache_ttl_seconds:
                    return entry["response"]
                else:
                    del self._cache[key]
        return None

    async def _put_in_cache(self, key: str, response: Dict[str, Any]) -> None:
        async with self._cache_lock:
            # Evict oldest if exceeding max size
            if len(self._cache) >= self.config.cache_max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
                del self._cache[oldest_key]
            self._cache[key] = {
                "timestamp": time.time(),
                "response": response,
            }

    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_content: str,
        response_format_json: bool = True,
        temperature: float = 0.1,
        context_type: str = "text",
    ) -> Dict[str, Any]:
        """
        Execute completion through Mistral AI with full safeguards.
        """
        if not self.config.mistral_api_key:
            return {
                "error": "MISTRAL_API_KEY is not configured on the router.",
                "code": "MISSING_API_KEY",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }

        # 1. Budget enforcement
        if self.usage_tracker.is_budget_exhausted():
            return {
                "error": f"Monthly token budget ({self.config.monthly_token_budget} tokens) exhausted.",
                "code": "BUDGET_EXHAUSTED",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }

        # 2. Input sanitization & bounding
        sanitized_input, was_truncated = bound_and_sanitize(
            user_content, max_chars=self.config.max_input_chars, context_type=context_type
        )

        # 3. Cache check
        cache_key = self._generate_cache_key(model, system_prompt, sanitized_input)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            self.usage_tracker.record_request(model=model, cache_hit=True)
            cached_result_copy = dict(cached_result)
            cached_result_copy["_cache_hit"] = True
            return cached_result_copy

        # 4. Rate-limiting & concurrency acquisition
        estimated_input_tokens = len(sanitized_input) // 4 + len(system_prompt) // 4
        await self.rate_limiter.acquire(estimated_tokens=estimated_input_tokens)

        # 5. Build payload
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sanitized_input},
        ]
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_output_tokens,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        # 6. HTTP Execution with retry loop
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                async with self.rate_limiter.semaphore:
                    client = await self.get_http_client()
                    resp = await client.post("https://api.mistral.ai/v1/chat/completions", json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]["message"]["content"]
                    usage_data = data.get("usage", {})
                    input_tok = usage_data.get("prompt_tokens", estimated_input_tokens)
                    output_tok = usage_data.get("completion_tokens", len(choice) // 4)

                    self.usage_tracker.record_request(
                        model=model,
                        input_tokens=input_tok,
                        output_tokens=output_tok,
                        success=True,
                    )

                    # Parse JSON if expected
                    parsed_content = choice
                    if response_format_json:
                        try:
                            parsed_content = json.loads(choice)
                        except Exception:
                            # Fallback if wrapped in markdown block
                            clean_str = choice.strip()
                            if clean_str.startswith("```json"):
                                clean_str = clean_str[7:-3].strip()
                            elif clean_str.startswith("```"):
                                clean_str = clean_str[3:-3].strip()
                            try:
                                parsed_content = json.loads(clean_str)
                            except Exception:
                                parsed_content = {"raw_output": choice}

                    result = {
                        "result": parsed_content,
                        "model": model,
                        "usage": {
                            "input_tokens": input_tok,
                            "output_tokens": output_tok,
                            "total_tokens": input_tok + output_tok,
                        },
                        "truncated": was_truncated,
                    }

                    # Cache successful result
                    await self._put_in_cache(cache_key, result)
                    return result

                elif resp.status_code == 429:
                    self.usage_tracker.record_request(model=model, success=False, is_429=True)
                    retry_after_hdr = resp.headers.get("Retry-After")
                    retry_after_val = float(retry_after_hdr) if retry_after_hdr else None
                    
                    if attempt < self.config.max_retries - 1:
                        backoff = self.rate_limiter.calculate_backoff(attempt, retry_after=retry_after_val)
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        return {
                            "error": "Mistral API rate limit exceeded (HTTP 429). Retries exhausted.",
                            "code": "RATE_LIMIT_EXCEEDED",
                            "status": 429,
                            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        }
                elif resp.status_code in (500, 502, 503, 504):
                    if attempt < self.config.max_retries - 1:
                        backoff = self.rate_limiter.calculate_backoff(attempt)
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        return {
                            "error": f"Mistral API server error (HTTP {resp.status_code}).",
                            "code": "MISTRAL_SERVER_ERROR",
                            "status": resp.status_code,
                            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        }
                else:
                    self.usage_tracker.record_request(model=model, success=False)
                    return {
                        "error": f"Mistral API returned HTTP {resp.status_code}: {resp.text}",
                        "code": f"HTTP_{resp.status_code}",
                        "status": resp.status_code,
                        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    }

            except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
                last_exception = exc
                if attempt < self.config.max_retries - 1:
                    backoff = self.rate_limiter.calculate_backoff(attempt)
                    await asyncio.sleep(backoff)
                    continue
                return {
                    "error": f"Request to Mistral AI timed out after {self.config.request_timeout_seconds}s.",
                    "code": "TIMEOUT",
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                }
            except Exception as exc:
                last_exception = exc
                self.usage_tracker.record_request(model=model, success=False)
                return {
                    "error": f"Mistral client error: {str(exc)}",
                    "code": "CLIENT_EXCEPTION",
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                }

        self.usage_tracker.record_request(model=model, success=False)
        return {
            "error": f"All retries failed. Last error: {str(last_exception)}",
            "code": "RETRIES_EXHAUSTED",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }
