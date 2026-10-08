# ARX Mistral MCP Router

> Production-ready AI delegation gateway connecting Google Antigravity to Mistral AI free-tier models on Oracle Cloud Infrastructure (OCI).

---

## Key Features

- **Cost-Optimized Delegation**: Offloads high-frequency deterministic tasks (extractions, log summaries, localized code checks, test generation, diff reviews) to Mistral free tier.
- **Strict Free-Tier Safety**: Enforces strict concurrency limits, RPS/TPM sliding windows, and a monthly token budget ceiling to prevent unexpected billing.
- **Deterministic Token Reductions**: Automatic ANSI code stripping, log deduplication, secret redaction, and bounded inputs.
- **In-Memory LRU Cache**: 24-hour cache preventing redundant API calls for identical requests.
- **OCI Ampere A1 ARM64 Ready**: Lightweight Python FastMCP / Starlette container ready for Coolify deployment at `arx-mcp.duckdns.org/mistral`.

---

## Exposed MCP Tools

1. `mistral_extract`: Structured evidence extraction from raw text.
2. `mistral_analyze_code`: Localized code diagnostics and refactoring review.
3. `mistral_generate_tests`: Automated unit & integration test generation.
4. `mistral_summarize_logs`: Diagnostic log summarization with deduplication.
5. `mistral_review_diff`: Advisory git diff review for regressions and security concerns.
6. `mistral_usage`: Real-time token consumption, 429 rate limit events, and savings metrics.

---

## Quick Start (Local Development)

```bash
# 1. Clone or navigate to the directory
cd arx-mistral-router

# 2. Configure environment
cp .env.example .env
# Set MISTRAL_API_KEY and MISTRAL_ROUTER_TOKEN in .env

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Run tests
pytest tests/

# 5. Start the server locally
python -m src.arx_router.server
```

---

## Integration with Antigravity

Add the following to your Antigravity MCP configuration:

```json
{
  "mcpServers": {
    "mistral-router": {
      "serverUrl": "https://arx-mcp.duckdns.org/mistral/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_MISTRAL_ROUTER_TOKEN"
      }
    }
  }
}
```
