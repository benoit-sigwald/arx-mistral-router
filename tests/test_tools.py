"""Tests for MCP tools and mocked Mistral API client."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from arx_router.tools import (
    run_extract,
    run_analyze_code,
    run_generate_tests,
    run_summarize_logs,
    run_review_diff,
    run_usage_report,
)
from arx_router.config import RouterConfig
from arx_router.mistral_client import MistralRouterClient
from arx_router.usage import UsageTracker
from arx_router.model_router import ModelRouter


@pytest.mark.asyncio
async def test_run_extract_mocked(mock_mistral_client, mock_model_router):
    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": '{"extracted_evidence": {"author": "Benoit"}, "source_references": ["by Benoit"]}'
                }
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20},
    }

    with patch.object(
        mock_mistral_client,
        "get_http_client",
        return_value=AsyncMock(
            post=AsyncMock(
                return_value=httpx.Response(
                    200,
                    json=mock_resp,
                    request=httpx.Request("POST", "http://test"),
                )
            )
        ),
    ):
        result = await run_extract(
            mock_mistral_client,
            mock_model_router,
            text="Document written by Benoit",
            instructions="Extract author",
        )
        assert "result" in result
        assert result["result"]["extracted_evidence"]["author"] == "Benoit"
        assert result["usage"]["input_tokens"] == 50
        assert result["usage"]["output_tokens"] == 20


@pytest.mark.asyncio
async def test_cache_hit_behavior(mock_mistral_client, mock_model_router):
    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": '{"findings": ["Clean code"]}'
                }
            }
        ],
        "usage": {"prompt_tokens": 30, "completion_tokens": 10},
    }

    mock_http = AsyncMock(
        post=AsyncMock(
            return_value=httpx.Response(
                200,
                json=mock_resp,
                request=httpx.Request("POST", "http://test"),
            )
        )
    )

    with patch.object(mock_mistral_client, "get_http_client", return_value=mock_http):
        # First call -> triggers HTTP post
        res1 = await run_analyze_code(mock_mistral_client, mock_model_router, code="x = 1", question="Check syntax")
        assert res1["result"]["findings"] == ["Clean code"]
        assert mock_http.post.call_count == 1

        # Second identical call -> served from cache
        res2 = await run_analyze_code(mock_mistral_client, mock_model_router, code="x = 1", question="Check syntax")
        assert res2["result"]["findings"] == ["Clean code"]
        assert res2.get("_cache_hit") is True
        assert mock_http.post.call_count == 1  # No additional HTTP call


@pytest.mark.asyncio
async def test_rate_limit_429_handling(mock_mistral_client, mock_model_router):
    mock_http = AsyncMock(
        post=AsyncMock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "0.01"},
                request=httpx.Request("POST", "http://test"),
            )
        )
    )

    with patch.object(mock_mistral_client, "get_http_client", return_value=mock_http):
        result = await run_summarize_logs(mock_mistral_client, mock_model_router, logs="error line 1")
        assert "error" in result
        assert result["code"] == "RATE_LIMIT_EXCEEDED"
        assert result["status"] == 429


@pytest.mark.asyncio
async def test_timeout_handling(mock_mistral_client, mock_model_router):
    mock_http = AsyncMock(
        post=AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))
    )

    with patch.object(mock_mistral_client, "get_http_client", return_value=mock_http):
        result = await run_generate_tests(
            mock_mistral_client,
            mock_model_router,
            code_or_module="def add(a, b): return a + b",
            framework="pytest",
        )
        assert "error" in result
        assert result["code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_missing_api_key_handling():
    no_key_config = RouterConfig(mistral_api_key="")
    no_key_client = MistralRouterClient(no_key_config)
    router = ModelRouter(no_key_config)

    result = await run_review_diff(no_key_client, router, diff="--- a\n+++ b")
    assert "error" in result
    assert result["code"] == "MISSING_API_KEY"


@pytest.mark.asyncio
async def test_budget_exhaustion_in_client():
    exhausted_tracker = UsageTracker(monthly_budget=100)
    exhausted_tracker.record_request("test", input_tokens=80, output_tokens=30, success=True)
    cfg = RouterConfig(mistral_api_key="key", monthly_token_budget=100)
    client = MistralRouterClient(cfg, usage_tracker=exhausted_tracker)
    router = ModelRouter(cfg)

    result = await run_extract(client, router, text="doc", instructions="inst")
    assert "error" in result
    assert result["code"] == "BUDGET_EXHAUSTED"
