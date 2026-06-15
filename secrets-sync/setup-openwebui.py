#!/usr/bin/env python3
"""
Auto-setup Open WebUI:
1. Create admin account
2. Upload AI Company tools
3. Configure system prompt
"""
import json, os, sys, time, urllib.request, urllib.error

BASE     = "http://localhost:8888"
ENV_FILE = "/opt/ai-company/infrastructure/.env"
TOOL_FILE = "/opt/ai-company/tools-api/openwebui_tools.py"

def get_env(key):
    try:
        for line in open(ENV_FILE):
            if line.startswith(f"{key}="):
                return line.split("=",1)[1].strip()
    except: pass
    return os.environ.get(key, "")

def req(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token: r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.load(resp), resp.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return {}, e.code

def wait_ready(max_wait=180):
    for _ in range(max_wait // 3):
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=3)
            return True
        except: pass
        time.sleep(3)
    return False

def main():
    print("  Waiting for Open WebUI...")
    if not wait_ready():
        print("  [!] Open WebUI not ready — skipping tool setup")
        return 1

    # Admin credentials
    admin_email    = get_env("WEBUI_ADMIN_EMAIL") or "admin@ai-company.local"
    admin_password = get_env("WEBUI_ADMIN_PASSWORD") or get_env("WEBUI_SECRET_KEY")[:16]
    admin_name     = "Admin"

    # Try signup (works on fresh install)
    print("  Creating admin account...")
    data, status = req("POST", "/api/v1/auths/signup", {
        "name": admin_name,
        "email": admin_email,
        "password": admin_password,
    })

    # Get token via signin
    print("  Signing in...")
    data, status = req("POST", "/api/v1/auths/signin", {
        "email": admin_email,
        "password": admin_password,
    })

    if status not in (200, 201) or "token" not in data:
        print(f"  [!] Sign-in failed ({status}) — tool upload skipped")
        print(f"      Create account manually at http://localhost:8888")
        return 1

    token = data["token"]
    print(f"  Signed in as {admin_email}")

    # Check if tool already exists
    tools_data, _ = req("GET", "/api/v1/tools/", token=token)
    existing = [t for t in (tools_data if isinstance(tools_data, list) else [])
                if t.get("name") == "AI Company Tools"]
    if existing:
        print("  [✓] Tool already exists — skipping")
        return 0

    # Read tool file
    try:
        tool_content = open(TOOL_FILE, encoding="utf-8").read()
    except:
        print(f"  [!] Tool file not found: {TOOL_FILE}")
        return 1

    # Upload tool
    print("  Uploading AI Company Tools...")
    data, status = req("POST", "/api/v1/tools/create", {
        "id":          "ai_company_tools",
        "name":        "AI Company Tools",
        "content":     tool_content,
        "meta":        {"description": "Generate mockups and create projects"},
    }, token=token)

    if status in (200, 201):
        print("  [✓] Tool uploaded successfully!")
        # Save credentials to .env
        for k, v in [("WEBUI_ADMIN_EMAIL", admin_email),
                     ("WEBUI_ADMIN_PASSWORD", admin_password)]:
            cur = get_env(k)
            if not cur:
                with open(ENV_FILE, "a") as f:
                    f.write(f"\n{k}={v}")
        return 0
    else:
        print(f"  [!] Tool upload failed ({status}): {data}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
