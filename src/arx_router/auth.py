"""ASGI TokenGuard authentication middleware for ARX Mistral MCP Router."""

from typing import Any, Callable, Dict, List
from .config import RouterConfig


class TokenGuard:
    """
    ASGI middleware enforcing Bearer token authentication and path-based token fallback.
    Matches the standard OCI MCP security conventions (einstein-mcp, prisme-mcp).
    """

    def __init__(self, app: Any, config: RouterConfig):
        self.app = app
        self.config = config
        self.tokens: List[str] = config.get_valid_tokens()
        self.allow_no_auth = config.allow_no_auth

        if not self.tokens and not self.allow_no_auth:
            raise RuntimeError(
                "MISTRAL_ROUTER_TOKEN / MISTRAL_ROUTER_TOKENS missing — refusing to start "
                "without authentication in production. (Set ALLOW_NO_AUTH=1 for local tests.)"
            )

        self.prefixes = [(f"/t/{t}", t) for t in self.tokens]
        self.bearers = {f"Bearer {t}" for t in self.tokens}

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")

            # 1. Health check endpoint (public, unauthenticated for Traefik / Coolify health monitoring)
            if path == "/healthz":
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"ok":true,"service":"arx-mistral-router","version":"1.0.0"}',
                })
                return

            # 2. OAuth discovery probes protection (Claude/Antigravity probe 404 handler)
            if "/.well-known/" in path or path.rstrip("/").endswith("/register"):
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error":"not_found"}',
                })
                return

            # 3. Authentication verification
            if self.tokens:
                headers = {
                    k.decode("latin-1").lower(): v.decode("latin-1")
                    for k, v in scope.get("headers", [])
                }
                auth_header = headers.get("authorization", "")

                matched_prefix = next((p for p, _ in self.prefixes if path.startswith(p + "/")), None)

                if auth_header in self.bearers:
                    # Authorized via header
                    pass
                elif matched_prefix:
                    # Authorized via /t/<token>/mcp URL path
                    new_scope = dict(scope)
                    new_scope["path"] = path[len(matched_prefix):]
                    new_scope["raw_path"] = new_scope["path"].encode("latin-1")
                    scope = new_scope
                else:
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": b'{"error":"unauthorized"}',
                    })
                    return

        await self.app(scope, receive, send)
