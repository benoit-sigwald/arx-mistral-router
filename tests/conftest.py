"""Test fixtures and mock configuration."""

import pytest
import os
import sys
from pathlib import Path

# Add src to sys.path
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from arx_router.config import RouterConfig
from arx_router.usage import UsageTracker
from arx_router.model_router import ModelRouter
from arx_router.mistral_client import MistralRouterClient


@pytest.fixture
def mock_config():
    return RouterConfig(
        mistral_api_key="test_mistral_api_key_1234567890",
        router_token="test_router_token_secret",
        router_tokens_extra="test_extra_token",
        allow_no_auth=False,
        monthly_token_budget=100000,
        rate_limit_rps=100.0,  # Fast for tests
        rate_limit_tpm=1000000,
        max_concurrent_requests=10,
        max_input_chars=1000,
        max_output_tokens=500,
        request_timeout_seconds=5.0,
        cache_ttl_seconds=3600,
    )


@pytest.fixture
def mock_usage_tracker():
    return UsageTracker(monthly_budget=100000)


@pytest.fixture
def mock_model_router(mock_config):
    return ModelRouter(mock_config)


@pytest.fixture
def mock_mistral_client(mock_config, mock_usage_tracker):
    return MistralRouterClient(mock_config, mock_usage_tracker)
