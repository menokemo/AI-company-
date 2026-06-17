#!/usr/bin/env python3
"""Auto-setup Portainer admin account."""
import json, os, sys, time, urllib.request, urllib.error

BASE     = os.environ.get("PORTAINER_URL", "https://localhost:9443")
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

def req(method, path, data=None, token=None):
    import ssl
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token: r.add_header("Authorization", f"Bearer {token}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(r, timeout=10, context=ctx) as resp:
            return json.load(resp), resp.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return {}, e.code

def wait_ready(max_wait=120):
    for _ in range(max_wait // 3):
        try:
            import ssl; ctx2=ssl.create_default_context(); ctx2.check_hostname=False; ctx2.verify_mode=ssl.CERT_NONE
            urllib.request.urlopen(f"{BASE}/api/status", timeout=3, context=ctx2)
            return True
        except: pass
        time.sleep(3)
    return False

def main():
    admin_user = get_env("PORTAINER_ADMIN_USER") or "admin"
    admin_pass = get_env("PORTAINER_ADMIN_PASSWORD")
    if not admin_pass:
        print("  [!] PORTAINER_ADMIN_PASSWORD not set"); return 1

    print("  Waiting for Portainer...")
    if not wait_ready():
        print("  [!] Portainer not ready"); return 1

    # Check if admin exists (try login)
    data, status = req("POST", "/api/auth", {
        "username": admin_user, "password": admin_pass
    })
    if status == 200:
        print("  [✓] Portainer already configured")
        return 0

    # Create admin
    print("  Creating Portainer admin...")
    data, status = req("POST", "/api/users/admin/init", {
        "username": admin_user, "password": admin_pass
    })
    if status in (200, 201, 204):
        print(f"  [✓] Portainer admin created: {admin_user}")
        set_env("PORTAINER_ADMIN_USER", admin_user)
        return 0
    else:
        print(f"  [!] Portainer setup failed ({status}): {data}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
