"""ARX Mistral MCP Router Server."""

import functools
import inspect
import json
import logging
import os
import sys
import threading
import time
import urllib.request
from typing import Any, Dict, List, Optional

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from .auth import TokenGuard
from .config import RouterConfig, get_config
from .mistral_client import MistralRouterClient
from .model_router import ModelRouter
from .tools import (
    run_analyze_code,
    run_extract,
    run_generate_tests,
    run_review_diff,
    run_summarize_logs,
    run_usage_report,
)
from .usage import get_usage_tracker

logger = logging.getLogger("arx_mistral_router")

config = get_config()
usage_tracker = get_usage_tracker(config.monthly_token_budget)
router = ModelRouter(config)
client = MistralRouterClient(config, usage_tracker)

mcp = FastMCP(
    "arx-mistral-router",
    instructions=(
        "ARX Mistral MCP Router: Cost-optimized AI delegation service for Antigravity. "
        "Delegates extraction, code analysis, test generation, log summarization, and diff reviews "
        "to Mistral AI free-tier models, conserving premium Gemini token quota. "
        "Responses are structured JSON with verified evidence, source quotes, and token metrics."
    ),
)


def _send_gate_telemetry(tool_name: str, duration_ms: int, success: bool) -> None:
    """Non-blocking telemetry to ARX Gate."""
    if not config.track_url:
        return

    def _worker():
        try:
            body = json.dumps({
                "site": config.track_site,
                "page": f"/mcp/{config.track_name}/{tool_name}",
                "ref": f"{'ok' if success else 'err'} {duration_ms}ms",
                "lang": "",
                "screen": "",
            }).encode("utf-8")
            req = urllib.request.Request(
                config.track_url,
                data=body,
                headers={
                    "Content-Type": "text/plain",
                    "User-Agent": f"mcp-{config.track_name}",
                },
            )
            urllib.request.urlopen(req, timeout=3).read()
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def track_mcp_tool(fn):
    """Decorator to track tool execution duration and gate telemetry."""
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            t0 = time.time()
            ok = True
            try:
                res = await fn(*args, **kwargs)
                return res
            except Exception:
                ok = False
                raise
            finally:
                ms = int((time.time() - t0) * 1000)
                _send_gate_telemetry(fn.__name__, ms, ok)
        return async_wrapper
    else:
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            t0 = time.time()
            ok = True
            try:
                res = fn(*args, **kwargs)
                return res
            except Exception:
                ok = False
                raise
            finally:
                ms = int((time.time() - t0) * 1000)
                _send_gate_telemetry(fn.__name__, ms, ok)
        return sync_wrapper


@mcp.tool()
@track_mcp_tool
async def mistral_extract(
    text: str,
    instructions: str,
    output_schema: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract structured evidence from raw text preserving strict source fidelity.
    Delegated to Mistral Small. Returns extracted evidence, source quotes, and token usage.
    """
    fit, reason = router.evaluate_delegation_fit("extract", text)
    if not fit:
        return {
            "error": reason,
            "code": "DELEGATION_REJECTED",
            "recommendation": "Execute in Gemini Pro",
        }
    return await run_extract(client, router, text, instructions, output_schema)


@mcp.tool()
@track_mcp_tool
async def mistral_analyze_code(
    code: str,
    question: str,
    constraints: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform localized code analysis, bug diagnosis, or refactoring inspection.
    Delegated to Mistral Code model. Returns findings, file locations, recommended changes, and uncertainty notes.
    """
    fit, reason = router.evaluate_delegation_fit("analyze_code", code)
    if not fit:
        return {
            "error": reason,
            "code": "DELEGATION_REJECTED",
            "recommendation": "Execute in Gemini Pro",
        }
    return await run_analyze_code(client, router, code, question, constraints)


@mcp.tool()
@track_mcp_tool
async def mistral_generate_tests(
    code_or_module: str,
    framework: str = "pytest",
    expected_behavior: str = "",
) -> Dict[str, Any]:
    """
    Generate automated unit or integration tests (pytest/jest/unittest) for functions and modules.
    Delegated to Mistral Code model. Returns runnable test code, edge cases covered, and assumptions.
    """
    fit, reason = router.evaluate_delegation_fit("generate_tests", code_or_module)
    if not fit:
        return {
            "error": reason,
            "code": "DELEGATION_REJECTED",
            "recommendation": "Execute in Gemini Pro",
        }
    return await run_generate_tests(client, router, code_or_module, framework, expected_behavior)


@mcp.tool()
@track_mcp_tool
async def mistral_summarize_logs(
    logs: str,
    objective: str = "Identify errors, root causes, and failures",
) -> Dict[str, Any]:
    """
    Diagnose and summarize system/application/deployment logs with automatic deduplication.
    Delegated to Mistral Small. Returns root cause candidates, relevant errors, excerpts, and recommended checks.
    """
    fit, reason = router.evaluate_delegation_fit("summarize_logs", logs)
    if not fit:
        return {
            "error": reason,
            "code": "DELEGATION_REJECTED",
            "recommendation": "Execute in Gemini Pro",
        }
    return await run_summarize_logs(client, router, logs, objective)


@mcp.tool()
@track_mcp_tool
async def mistral_review_diff(
    diff: str,
    requirements: str = "",
    test_results: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform an advisory code review on a git diff.
    Delegated to Mistral Code model. Returns potential regressions, security risks, missing tests, and suggested fixes.
    """
    fit, reason = router.evaluate_delegation_fit("review_diff", diff)
    if not fit:
        return {
            "error": reason,
            "code": "DELEGATION_REJECTED",
            "recommendation": "Execute in Gemini Pro",
        }
    return await run_review_diff(client, router, diff, requirements, test_results)


@mcp.tool()
@track_mcp_tool
def mistral_usage() -> Dict[str, Any]:
    """
    Retrieve local usage statistics, monthly budget health, 429 rate limit events, and estimated Gemini token savings.
    """
    return run_usage_report(usage_tracker)


def build_app(cfg: Optional[RouterConfig] = None):
    """Build ASGI application wrapped with TokenGuard authentication."""
    active_config = cfg or get_config()
    if hasattr(mcp, "http_app"):
        raw_app = mcp.http_app()
    elif hasattr(mcp, "streamable_http_app"):
        raw_app = mcp.streamable_http_app()
    else:
        raise AttributeError("FastMCP instance has neither http_app nor streamable_http_app")
    return TokenGuard(raw_app, active_config)


def create_asgi_app():
    """ASGI application entrypoint for uvicorn."""
    return build_app()


# Default ASGI application instance
app = build_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
