# Coolify Deployment Guide — ARX Mistral MCP Router

## 1. Overview & Architecture

- **Host**: OCI Ampere A1 (ARM64 Ubuntu 24.04), `145.241.174.15`
- **Domain**: `https://arx-mcp.duckdns.org/mistral` (Option A — subpath routing under `arx-mcp`)
- **Reverse Proxy**: Coolify Traefik v3.6 (terminating Let's Encrypt TLS)
- **Port**: Container listens on `8000`
- **Resource Footprint**: Minimal (~100 MB RAM, < 0.1 OCPU idle)

---

## 2. Coolify Application Setup (API or Dashboard)

### Via Coolify Dashboard (`http://145.241.174.15:8000`):

1. **New Resource** → **Application** → **Public Repository** (or private with GitHub App).
2. **Git Repository**: `https://github.com/benoit-sigwald/arx-mistral-router`
3. **Branch**: `main`
4. **Build Pack**: `Dockerfile`
5. **Domains**: `https://arx-mcp.duckdns.org/mistral`
6. **Exposed Port**: `8000`
7. **Health Check Path**: `/healthz`

### Environment Variables to Configure in Coolify:

| Variable | Recommended Value | Scope | Description |
|---|---|---|---|
| `MISTRAL_API_KEY` | `<your_mistral_api_key>` | Secret (Container) | Mistral Free Tier API Key |
| `MISTRAL_ROUTER_TOKEN` | `<generated_random_bearer_token>` | Secret (Container) | Antigravity client authentication token |
| `MODEL_EXTRACTION` | `mistral-small-latest` | Public | Model for structured extraction |
| `MODEL_SUMMARIZATION` | `mistral-small-latest` | Public | Model for log diagnostics |
| `MODEL_CODE` | `codestral-latest` | Public | Model for localized code analysis |
| `MODEL_TESTS` | `codestral-latest` | Public | Model for test generation |
| `MODEL_DIFF` | `codestral-latest` | Public | Model for git diff review |
| `RATE_LIMIT_RPS` | `1.0` | Public | Free tier rate limit (req/s) |
| `MONTHLY_TOKEN_BUDGET`| `1000000` | Public | Safety ceiling for token usage |
| `MAX_CONCURRENT_REQUESTS`| `2` | Public | Max parallel upstream requests |

---

## 3. Verification Commands

Once deployed:

```bash
# 1. Health check (public, unauthenticated)
curl -s https://arx-mcp.duckdns.org/mistral/healthz
# Expected: {"ok":true,"service":"arx-mistral-router","version":"1.0.0"}

# 2. OAuth probe rejection (must return 404 to avoid OAuth loops)
curl -s -o /dev/null -w "%{http_code}\n" https://arx-mcp.duckdns.org/mistral/.well-known/oauth-protected-resource
# Expected: 404

# 3. Unauthenticated request rejection (must return 401)
curl -s -o /dev/null -w "%{http_code}\n" https://arx-mcp.duckdns.org/mistral/mcp
# Expected: 401

# 4. Authenticated tool discovery
curl -s -H "Authorization: Bearer <MISTRAL_ROUTER_TOKEN>" https://arx-mcp.duckdns.org/mistral/mcp
```

---

## 4. Rollback Procedure

If any issue occurs during deployment:
1. In Coolify dashboard, select **Deployments** → **Rollback** to the previous stable release commit.
2. Alternatively, if container fails to start, re-trigger deployment with `ALLOW_NO_AUTH=1` temporarily to check container logs without traffic.
3. Existing MCP services (`einstein`, `prisme`, `omni`, `blackstone`) run in isolated containers and will NOT be affected.
