"""Tests for TokenGuard authentication middleware."""

import pytest
import httpx
from arx_router.auth import TokenGuard
from arx_router.config import RouterConfig


async def dummy_app(scope, receive, send):
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({
        "type": "http.response.body",
        "body": b'{"ok": true, "path": "' + scope.get("path", "").encode() + b'"}',
    })


@pytest.mark.asyncio
async def test_healthz_unauthenticated():
    cfg = RouterConfig(router_token="secret_token", allow_no_auth=False)
    app = TokenGuard(dummy_app, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["service"] == "arx-mistral-router"


@pytest.mark.asyncio
async def test_oauth_probes_return_404():
    cfg = RouterConfig(router_token="secret_token", allow_no_auth=False)
    app = TokenGuard(dummy_app, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 404
        resp_reg = await client.post("/register")
        assert resp_reg.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_rejection():
    cfg = RouterConfig(router_token="secret_token", allow_no_auth=False)
    app = TokenGuard(dummy_app, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # No header
        resp = await client.get("/mcp")
        assert resp.status_code == 401
        # Invalid header
        resp_bad = await client.get("/mcp", headers={"Authorization": "Bearer wrong_token"})
        assert resp_bad.status_code == 401


@pytest.mark.asyncio
async def test_bearer_authorized():
    cfg = RouterConfig(router_token="secret_token", allow_no_auth=False)
    app = TokenGuard(dummy_app, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/mcp", headers={"Authorization": "Bearer secret_token"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_path_token_fallback():
    cfg = RouterConfig(router_token="secret_token", allow_no_auth=False)
    app = TokenGuard(dummy_app, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/t/secret_token/mcp")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["path"] == "/mcp"
