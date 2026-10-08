"""Configuration management for ARX Mistral MCP Router."""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class RouterConfig:
    # Authentication & API Keys
    mistral_api_key: str = field(
        default_factory=lambda: os.getenv("MISTRAL_API_KEY", "")
    )
    router_token: str = field(
        default_factory=lambda: os.getenv("MISTRAL_ROUTER_TOKEN", "")
    )
    router_tokens_extra: str = field(
        default_factory=lambda: os.getenv("MISTRAL_ROUTER_TOKENS", "")
    )
    allow_no_auth: bool = field(
        default_factory=lambda: os.getenv("ALLOW_NO_AUTH", "0").lower() in ("1", "true", "yes")
    )

    # Model Mappings (Task to Model)
    model_extraction: str = field(
        default_factory=lambda: os.getenv("MODEL_EXTRACTION", "mistral-small-latest")
    )
    model_summarization: str = field(
        default_factory=lambda: os.getenv("MODEL_SUMMARIZATION", "mistral-small-latest")
    )
    model_code: str = field(
        default_factory=lambda: os.getenv("MODEL_CODE", "codestral-latest")
    )
    model_tests: str = field(
        default_factory=lambda: os.getenv("MODEL_TESTS", "codestral-latest")
    )
    model_diff: str = field(
        default_factory=lambda: os.getenv("MODEL_DIFF", "codestral-latest")
    )
    fallback_model: str = field(
        default_factory=lambda: os.getenv("MODEL_FALLBACK", "mistral-small-latest")
    )

    # Free Tier & Rate Limits
    rate_limit_rps: float = field(
        default_factory=lambda: float(os.getenv("RATE_LIMIT_RPS", "1.0"))
    )
    rate_limit_tpm: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_TPM", "60000"))
    )
    monthly_token_budget: int = field(
        default_factory=lambda: int(os.getenv("MONTHLY_TOKEN_BUDGET", "1000000"))
    )
    max_concurrent_requests: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    )
    max_input_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_INPUT_CHARS", "32000"))
    )
    max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
    )
    request_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30.0"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )

    # Caching
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "86400"))
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("CACHE_MAX_SIZE", "256"))
    )

    # Server Runtime
    port: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8000"))
    )
    host: str = field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0")
    )

    # Tracking & Gate Telemetry
    track_url: str = field(
        default_factory=lambda: os.getenv("TRACK_URL", "https://arx-apps.duckdns.org/gate/t")
    )
    track_site: str = field(
        default_factory=lambda: os.getenv("TRACK_SITE", "arxcapital")
    )
    track_name: str = field(
        default_factory=lambda: os.getenv("TRACK_NAME", "mistral-router")
    )

    def get_valid_tokens(self) -> List[str]:
        tokens = []
        if self.router_token.strip():
            tokens.append(self.router_token.strip())
        if self.router_tokens_extra.strip():
            for t in self.router_tokens_extra.split(","):
                clean = t.strip()
                if clean and clean not in tokens:
                    tokens.append(clean)
        return tokens


def get_config() -> RouterConfig:
    return RouterConfig()
