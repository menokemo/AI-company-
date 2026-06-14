#!/usr/bin/env python3
"""
Auto-setup Infisical on first install:
1. Create admin account
2. Create organization + project
3. Create Machine Identity
4. Get Client ID + Secret
5. Save to .env
"""
import json, os, sys, time, urllib.request, urllib.error, secrets

BASE = "http://localhost:8080"
ENV_FILE = "/opt/ai-company/infrastructure/.env"

def req(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.load(resp), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code

def get_env(key):
    try:
        for line in open(ENV_FILE):
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    except: pass
    return ""

def set_env(key, value):
    """Update or add a key in .env"""
    try:
        lines = open(ENV_FILE).readlines()
    except:
        lines = []
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)

def wait_for_infisical(max_wait=120):
    print("  Waiting for Infisical API...")
    for i in range(max_wait // 3):
        try:
            urllib.request.urlopen(f"{BASE}/api/v1/healthcheck", timeout=3)
            print("  Infisical is ready")
            return True
        except: pass
        time.sleep(3)
    return False

def main():
    # Check if already configured
    if get_env("INFISICAL_CLIENT_ID") and get_env("INFISICAL_CLIENT_SECRET"):
        print("[✓] Infisical already configured — skipping setup")
        return 0

    print("[→] Auto-configuring Infisical...")

    if not wait_for_infisical():
        print("[✗] Infisical not reachable")
        return 1

    # Read generated admin credentials from .env
    admin_email    = get_env("INFISICAL_ADMIN_EMAIL") or "admin@ai-company.local"
    admin_password = get_env("INFISICAL_ADMIN_PASSWORD") or secrets.token_urlsafe(16)

    # ── Step 1: Create admin account ──────────────────────────────────────
    print("  Creating admin account...")
    data, status = req("POST", "/api/v1/auth/signup/email/signup", {
        "email": admin_email
    })

    if status not in (200, 201):
        # Try login (account might already exist)
        print(f"  Signup failed ({status}) — trying login...")
    else:
        # Complete signup (self-hosted skips email verification)
        token_val = data.get("token", "")
        data2, status2 = req("POST", "/api/v1/auth/signup/email/complete", {
            "email": admin_email,
            "password": admin_password,
            "token": token_val,
            "firstName": "Admin",
            "lastName": "AI-Company",
        })
        if status2 not in (200, 201):
            print(f"  Signup complete failed ({status2}): {data2}")

    # ── Step 2: Login ──────────────────────────────────────────────────────
    print("  Logging in...")
    data, status = req("POST", "/api/v1/auth/login1", {
        "email": admin_email,
        "clientPublicKey": "dummy"
    })

    if status not in (200, 201):
        print(f"  Login1 failed ({status}): {data}")
        return 1

    # Try direct login
    data, status = req("POST", "/api/v3/auth/login", {
        "email": admin_email,
        "password": admin_password,
    })

    if status not in (200, 201):
        print(f"  Login failed ({status}): {data}")
        return 1

    access_token = data.get("token") or data.get("accessToken") or data.get("access_token")
    if not access_token:
        print(f"  No token in response: {list(data.keys())}")
        return 1

    print(f"  Logged in successfully")

    # ── Step 3: Get or create organization ────────────────────────────────
    print("  Setting up organization...")
    data, status = req("GET", "/api/v1/organization", token=access_token)
    orgs = data.get("organizations", [])

    if orgs:
        org_id = orgs[0]["id"]
        print(f"  Using existing org: {orgs[0].get('name')}")
    else:
        data, status = req("POST", "/api/v1/organization", {
            "name": "AI Company"
        }, token=access_token)
        org_id = data.get("organization", {}).get("id")
        print(f"  Created org: {org_id}")

    # ── Step 4: Get or create project ─────────────────────────────────────
    print("  Setting up project...")
    data, status = req("GET", f"/api/v1/organization/{org_id}/workspaces",
                       token=access_token)
    workspaces = data.get("workspaces", [])

    if workspaces:
        proj_id = workspaces[0]["id"]
        print(f"  Using existing project: {workspaces[0].get('name')}")
    else:
        data, status = req("POST", "/api/v2/workspace", {
            "workspaceName": "ai-company",
            "organizationId": org_id,
        }, token=access_token)
        proj_id = data.get("workspace", {}).get("id")
        print(f"  Created project: {proj_id}")

    # ── Step 5: Create Machine Identity ───────────────────────────────────
    print("  Creating Machine Identity...")
    data, status = req("POST", "/api/v1/auth/universal-auth/identities", {
        "name": "ai-company-sync",
        "organizationId": org_id,
    }, token=access_token)

    if status not in (200, 201):
        # Try identities endpoint
        data, status = req("POST", "/api/v1/identities", {
            "name": "ai-company-sync",
            "organizationId": org_id,
            "role": "admin",
        }, token=access_token)

    identity_id = (data.get("identity") or data.get("machineIdentity") or data).get("id")
    if not identity_id:
        print(f"  Could not create Machine Identity: {data}")
        return 1

    # Enable Universal Auth
    data, status = req("POST", f"/api/v1/auth/universal-auth/identities/{identity_id}",
                       {}, token=access_token)
    client_id = data.get("identityUniversalAuth", {}).get("clientId") or identity_id

    # Create Client Secret
    data, status = req("POST",
        f"/api/v1/auth/universal-auth/identities/{identity_id}/client-secrets",
        {"description": "auto-generated by install script"},
        token=access_token)

    client_secret = (data.get("clientSecretData") or data).get("clientSecret") or \
                    data.get("secret", {}).get("clientSecret")

    if not client_secret:
        print(f"  Could not get client secret: {data}")
        return 1

    # ── Step 6: Add identity to project ───────────────────────────────────
    req("POST", f"/api/v2/workspace/{proj_id}/identity-memberships/{identity_id}",
        {"role": "admin"}, token=access_token)

    # ── Step 7: Save to .env ──────────────────────────────────────────────
    print("  Saving credentials to .env...")
    set_env("INFISICAL_CLIENT_ID", client_id)
    set_env("INFISICAL_CLIENT_SECRET", client_secret)
    set_env("INFISICAL_PROJECT_ID", proj_id)

    print(f"[✓] Infisical auto-configured!")
    print(f"    Client ID: {client_id}")
    print(f"    Project ID: {proj_id}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
