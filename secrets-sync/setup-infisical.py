#!/usr/bin/env python3
"""
Auto-setup Infisical:
1. Create admin account
2. Create organization + project
3. Create Machine Identity with Universal Auth
4. Save credentials to .env
"""
import json, os, sys, time, urllib.request, urllib.error

BASE     = "http://localhost:8080"
ENV_FILE = "/opt/ai-company/infrastructure/.env"

def get_env(key):
    try:
        for line in open(ENV_FILE):
            if line.startswith(f"{key}="):
                return line.split("=",1)[1].strip()
    except: pass
    return os.environ.get(key, "")

def set_env(key, value):
    try: lines = open(ENV_FILE).readlines()
    except: lines = []
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n"); found = True
        else:
            new_lines.append(line)
    if not found: new_lines.append(f"{key}={value}\n")
    open(ENV_FILE, "w").writelines(new_lines)

def req(method, path, data=None, token=None, base=None):
    url = (base or BASE) + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token: r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            try: return json.load(resp), resp.status
            except: return {}, resp.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return {}, e.code

def wait_ready(max_wait=120):
    for _ in range(max_wait // 3):
        try:
            urllib.request.urlopen(f"{BASE}/api/v1/healthcheck", timeout=3)
            return True
        except: pass
        time.sleep(3)
    return False

def main():
    # Skip if already configured
    if get_env("INFISICAL_CLIENT_ID") and get_env("INFISICAL_CLIENT_SECRET"):
        print("  [✓] Infisical already configured")
        return 0

    print("  Waiting for Infisical...")
    if not wait_ready():
        print("  [!] Infisical not ready"); return 1

    email    = get_env("INFISICAL_ADMIN_EMAIL") or "admin@ai-company.local"
    password = get_env("INFISICAL_ADMIN_PASSWORD")
    if not password:
        print("  [!] INFISICAL_ADMIN_PASSWORD not set"); return 1

    # ── Step 1: Create admin (signup) ────────────────────────────────
    print("  Creating admin account...")
    req("POST", "/api/v1/auth/signup/email/signup", {"email": email})
    # Complete signup (self-hosted skips email verification in some versions)
    req("POST", "/api/v1/auth/signup/email/complete", {
        "email": email, "password": password,
        "firstName": "Admin", "lastName": "AI-Company", "token": ""
    })

    # ── Step 2: Login ─────────────────────────────────────────────────
    print("  Logging in...")
    # Try v3 login first (newer Infisical)
    for login_path in ["/api/v3/auth/login", "/api/v1/auth/login"]:
        data, status = req("POST", login_path, {"email": email, "password": password})
        if status in (200, 201):
            token = data.get("token") or data.get("accessToken") or data.get("access_token")
            if token: break
    else:
        print(f"  [!] Login failed — open http://localhost:8080 to create account manually")
        return 1

    print(f"  Logged in as {email}")

    # ── Step 3: Organization ──────────────────────────────────────────
    data, _ = req("GET", "/api/v1/organization", token=token)
    orgs = data.get("organizations", [])
    if orgs:
        org_id = orgs[0]["id"]
        print(f"  Using org: {orgs[0].get('name')}")
    else:
        data, _ = req("POST", "/api/v1/organization", {"name": "AI Company"}, token=token)
        org_id = (data.get("organization") or data).get("id","")
        print(f"  Created org: {org_id[:8]}...")

    # ── Step 4: Project ───────────────────────────────────────────────
    data, _ = req("GET", f"/api/v1/organization/{org_id}/workspaces", token=token)
    workspaces = data.get("workspaces", [])
    if workspaces:
        proj_id = workspaces[0]["id"]
        proj_name = workspaces[0].get("name","ai-company")
        print(f"  Using project: {proj_name}")
    else:
        data, _ = req("POST", "/api/v2/workspace",
                     {"workspaceName": "ai-company", "organizationId": org_id}, token=token)
        proj_id = (data.get("workspace") or data).get("id","")
        print(f"  Created project: {proj_id[:8]}...")

    # ── Step 5: Machine Identity ──────────────────────────────────────
    print("  Creating Machine Identity...")
    # Create identity
    data, status = req("POST", "/api/v1/identities",
                      {"name": "ai-company-sync", "organizationId": org_id, "role": "admin"},
                      token=token)
    identity = data.get("identity") or data
    identity_id = identity.get("id", "")

    if not identity_id:
        print(f"  [!] Could not create Machine Identity ({status})")
        return 1

    # Enable Universal Auth
    req("POST", f"/api/v1/auth/universal-auth/identities/{identity_id}", {}, token=token)

    # Get Client ID
    data, _ = req("GET", f"/api/v1/auth/universal-auth/identities/{identity_id}", token=token)
    client_id = (data.get("identityUniversalAuth") or data).get("clientId") or identity_id

    # Create Client Secret
    data, _ = req("POST", f"/api/v1/auth/universal-auth/identities/{identity_id}/client-secrets",
                 {"description": "auto-generated"}, token=token)
    client_secret = (data.get("clientSecretData") or data).get("clientSecret","")

    if not client_secret:
        print(f"  [!] Could not get client secret")
        return 1

    # Add identity to project
    req("POST", f"/api/v2/workspace/{proj_id}/identity-memberships/{identity_id}",
       {"role": "admin"}, token=token)

    # ── Step 6: Save to .env ─────────────────────────────────────────
    print("  Saving credentials...")
    set_env("INFISICAL_CLIENT_ID", client_id)
    set_env("INFISICAL_CLIENT_SECRET", client_secret)
    set_env("INFISICAL_PROJECT_ID", proj_id)

    print(f"  [✓] Infisical configured!")
    print(f"      Login: {email}")
    print(f"      URL:   http://localhost:8080")
    return 0

if __name__ == "__main__":
    sys.exit(main())
