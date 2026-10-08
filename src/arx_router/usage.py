"""Usage tracker, metrics aggregator, and budget monitoring."""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class ModelUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    rate_limit_events: int = 0
    cache_hits: int = 0


class UsageTracker:
    def __init__(self, monthly_budget: int = 1000000):
        self._lock = threading.Lock()
        self.monthly_budget = monthly_budget
        self.models: Dict[str, ModelUsage] = {}
        self.month_start = datetime.now(timezone.utc).strftime("%Y-%m")
        self.total_delegations: int = 0
        self.total_cache_hits: int = 0
        self.last_activity: float = time.time()

    def record_request(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        is_429: bool = False,
        cache_hit: bool = False,
    ) -> None:
        with self._lock:
            self._check_month_rollover()
            if model not in self.models:
                self.models[model] = ModelUsage(model=model)

            m = self.models[model]
            m.requests_total += 1
            if cache_hit:
                m.cache_hits += 1
                self.total_cache_hits += 1
                m.requests_success += 1
                self.total_delegations += 1
                return

            if success:
                m.requests_success += 1
                m.input_tokens += input_tokens
                m.output_tokens += output_tokens
                m.total_tokens += (input_tokens + output_tokens)
                self.total_delegations += 1
            else:
                m.requests_failed += 1
                if is_429:
                    m.rate_limit_events += 1

            self.last_activity = time.time()

    def _check_month_rollover(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if current_month != self.month_start:
            self.month_start = current_month
            self.models.clear()
            self.total_delegations = 0
            self.total_cache_hits = 0

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            self._check_month_rollover()
            total_input = sum(m.input_tokens for m in self.models.values())
            total_output = sum(m.output_tokens for m in self.models.values())
            total_tokens = total_input + total_output
            total_requests = sum(m.requests_total for m in self.models.values())
            total_success = sum(m.requests_success for m in self.models.values())
            total_failed = sum(m.requests_failed for m in self.models.values())
            total_429 = sum(m.rate_limit_events for m in self.models.values())

            budget_used_pct = round((total_tokens / self.monthly_budget) * 100, 2) if self.monthly_budget > 0 else 0.0
            remaining_budget = max(0, self.monthly_budget - total_tokens)

            # Standard theoretical Gemini 1.5/2.0 Pro / Flash baseline pricing for comparison ($/1M tokens)
            # Gemini Pro baseline ~$1.25 / 1M input, $5.00 / 1M output
            estimated_gemini_equivalent_usd = round(
                (total_input / 1_000_000 * 1.25) + (total_output / 1_000_000 * 5.00), 4
            )

            models_breakdown = {}
            for name, m in self.models.items():
                models_breakdown[name] = {
                    "input_tokens": m.input_tokens,
                    "output_tokens": m.output_tokens,
                    "total_tokens": m.total_tokens,
                    "requests_total": m.requests_total,
                    "requests_success": m.requests_success,
                    "requests_failed": m.requests_failed,
                    "rate_limit_429_events": m.rate_limit_events,
                    "cache_hits": m.cache_hits,
                }

            return {
                "period": self.month_start,
                "provider": "Mistral AI (Free Tier)",
                "actual_cost_usd": 0.0,
                "budget": {
                    "monthly_token_budget": self.monthly_budget,
                    "tokens_consumed": total_tokens,
                    "tokens_remaining": remaining_budget,
                    "budget_used_percent": budget_used_pct,
                    "budget_exhausted": total_tokens >= self.monthly_budget,
                },
                "totals": {
                    "total_delegations": self.total_delegations,
                    "total_requests": total_requests,
                    "successful_requests": total_success,
                    "failed_requests": total_failed,
                    "rate_limit_429_events": total_429,
                    "total_cache_hits": self.total_cache_hits,
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "total_tokens": total_tokens,
                },
                "estimated_gemini_tokens_saved": total_tokens,
                "estimated_gemini_cost_saved_usd": estimated_gemini_equivalent_usd,
                "models": models_breakdown,
            }

    def is_budget_exhausted(self) -> bool:
        with self._lock:
            self._check_month_rollover()
            total_tokens = sum(m.total_tokens for m in self.models.values())
            return total_tokens >= self.monthly_budget


_GLOBAL_TRACKER: UsageTracker = None


def get_usage_tracker(monthly_budget: int = 1000000) -> UsageTracker:
    global _GLOBAL_TRACKER
    if _GLOBAL_TRACKER is None:
        _GLOBAL_TRACKER = UsageTracker(monthly_budget=monthly_budget)
    return _GLOBAL_TRACKER
