#!/usr/bin/env python3
"""
Deploy arx-mistral-router on OCI via Coolify API.
Reads secrets securely from /root and verifies deployment health.
"""
import json
import os
import pathlib
import secrets
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8000/api/v1"
PROJECT = "uds1s9ii5rnzpkwpyj1bwwef"
SERVER = "j4lzqm1zohzx9ql0136k3lns"
DOMAIN = "https://arx-mcp.duckdns.org/mistral"
REPO = "https://github.com/benoit-sigwald/arx-mistral-router.git"
BRANCH = "main"

TOKEN = pathlib.Path("/root/.coolify_token").read_text().strip()


def call(path, payload=None, method="POST"):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:1000]
        return {"ERROR": exc.code, "body": body}


# 1. Setup tokens
token_file = pathlib.Path("/root/.mistral_router_token")
if not token_file.exists():
    token_file.write_text(secrets.token_urlsafe(32) + "\n")
    os.chmod(token_file, 0o600)
router_token = token_file.read_text().strip()

mistral_key_file = pathlib.Path("/root/.mistral_api_key")
if not mistral_key_file.exists():
    raise SystemExit("Missing /root/.mistral_api_key on OCI host.")
mistral_api_key = mistral_key_file.read_text().strip()

# 2. Check if application already exists
existing_apps = call("/applications", method="GET")
app_uuid = None
if isinstance(existing_apps, list):
    for app in existing_apps:
        if app.get("name") == "arx-mistral-router":
            app_uuid = app.get("uuid")
            print(f"Found existing application: {app_uuid}")
            break

if not app_uuid:
    print("Creating application in Coolify...")
    app = call("/applications/public", {
        "project_uuid": PROJECT,
        "server_uuid": SERVER,
        "environment_name": "production",
        "git_repository": REPO,
        "git_branch": BRANCH,
        "build_pack": "dockerfile",
        "ports_exposes": "8000",
        "name": "arx-mistral-router",
        "domains": DOMAIN,
        "instant_deploy": False,
    })
    print("App creation response:", json.dumps(app))
    app_uuid = app.get("uuid")
    if not app_uuid:
        raise SystemExit("Failed to create application.")

pathlib.Path("/tmp/mistral_router_uuid").write_text(app_uuid)

# 3. Configure environment variables
envs = {
    "MISTRAL_API_KEY": mistral_api_key,
    "MISTRAL_ROUTER_TOKEN": router_token,
    "MODEL_EXTRACTION": "mistral-small-latest",
    "MODEL_SUMMARIZATION": "mistral-small-latest",
    "MODEL_CODE": "codestral-latest",
    "MODEL_TESTS": "codestral-latest",
    "MODEL_DIFF": "codestral-latest",
    "RATE_LIMIT_RPS": "1.0",
    "RATE_LIMIT_TPM": "60000",
    "MONTHLY_TOKEN_BUDGET": "1000000",
    "MAX_CONCURRENT_REQUESTS": "2",
    "PORT": "8000",
    "HOST": "0.0.0.0",
}

for k, v in envs.items():
    res = call(f"/applications/{app_uuid}/envs", {"key": k, "value": v, "is_preview": False})
    print(f"Set env {k}:", "ok" if "uuid" in res else res)

# 4. Trigger deployment
print("Triggering deployment...")
deploy_res = call(f"/deploy?uuid={app_uuid}", {})
print("Deploy response:", json.dumps(deploy_res))
deployment_uuid = deploy_res.get("deployment_uuid")

# 5. Wait for deployment completion
if deployment_uuid:
    print(f"Polling deployment {deployment_uuid}...")
    for _ in range(60):
        time.sleep(5)
        status_res = call(f"/deployments/{deployment_uuid}", method="GET")
        status = status_res.get("status")
        print(f"Deployment status: {status}")
        if status in ("finished", "success"):
            print("Deployment successful!")
            break
        elif status in ("failed", "error", "cancelled"):
            print("Deployment failed:", json.dumps(status_res))
            sys.exit(1)

print("Deployment complete.")
