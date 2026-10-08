"""Tests for FastMCP server and tool registration."""

import pytest
from arx_router.server import mcp, build_app
from arx_router.config import RouterConfig


@pytest.mark.asyncio
async def test_mcp_tools_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "mistral_extract" in tool_names
    assert "mistral_analyze_code" in tool_names
    assert "mistral_generate_tests" in tool_names
    assert "mistral_summarize_logs" in tool_names
    assert "mistral_review_diff" in tool_names
    assert "mistral_usage" in tool_names


def test_build_app_with_auth():
    cfg = RouterConfig(router_token="prod_secret_token", allow_no_auth=False)
    app = build_app(cfg)
    assert app is not None
    assert app.tokens == ["prod_secret_token"]
