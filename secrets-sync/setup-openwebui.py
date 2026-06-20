#!/usr/bin/env python3
"""
Auto-setup Open WebUI:
1. Create admin account
2. Upload AI Company tools
3. Configure system prompt
"""
import json, os, sys, time, urllib.request, urllib.error, socket

# Auto-detect if running inside Docker or on host
def get_openwebui_url():
    # Check explicit environment variable first
    if "OPENWEBUI_URL" in os.environ:
        return os.environ["OPENWEBUI_URL"]
    if "OPENWEBUI_API_URL" in os.environ:
        return os.environ["OPENWEBUI_API_URL"]
    
    # Try to detect if we're inside Docker
    try:
        # If we can resolve ai-open-webui, we're in the docker network
        socket.gethostbyname("ai-open-webui")
        return "http://ai-open-webui:8080"  # Inside Docker
    except socket.gaierror:
        # Can't resolve docker hostname, must be on host
        host_ip = os.environ.get("HOST_IP", "192.168.2.29")
        return f"http://{host_ip}:8888"  # On host

BASE     = get_openwebui_url()
INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")
BASE_DIR = INSTALL_DIR
TOOL_FILE   = os.path.join(BASE_DIR, "tools-api", "openwebui_tools.py")

# Increased timeouts and retry configuration
REQUEST_TIMEOUT = 60  # 60 seconds per request
MAX_RETRIES = 5
RETRY_DELAY = 5

def get_env(key):
    try:
        for line in open(ENV_FILE):
            if line.startswith(f"{key}="):
                return line.split("=",1)[1].strip()
    except: pass
    return os.environ.get(key, "")

def req(method, path, data=None, token=None, retry=MAX_RETRIES):
    """Make HTTP request with retry logic"""
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    r.add_header("User-Agent", "AI-Company-Setup/1.0")
    if token: r.add_header("Authorization", f"Bearer {token}")
    
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(r, timeout=REQUEST_TIMEOUT) as resp:
                return json.load(resp), resp.status
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read().decode()), e.code
            except: return {}, e.code
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retry - 1:
                print(f"    [⚠] Connection error, retrying in {RETRY_DELAY}s... (attempt {attempt+1}/{retry})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"    [!] Failed after {retry} attempts: {e}")
                return {}, 0
    return {}, 0

def wait_ready(max_wait=60):
    """Wait for Open WebUI to be ready using curl"""
    import subprocess
    import time
    
    print(f"  Waiting for Open WebUI (max {max_wait}s)...")
    
    for second in range(1, max_wait + 1):
        try:
            result = subprocess.run(
                ["curl", "-sf", "-m", "2", f"{BASE}/"],
                capture_output=True,
                timeout=3
            )
            
            # returncode 0 = success
            if result.returncode == 0:
                print(f"\n  [✓] Open WebUI is ready! (after {second}s)")
                return True
        except Exception as e:
            pass
        
        # Progress indicator
        if second % 10 == 0:
            print(f"    Still waiting... [{second}s/{max_wait}s]", end="\r")
        
        time.sleep(1)
    
    print(f"\n  [!] Timeout after {max_wait}s - Open WebUI not responding")
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

    # Check if tool already exists — لو موجود، نتخطى رفعه بس نكمّل لباقي الإعدادات
    tools_data, _ = req("GET", "/api/v1/tools/", token=token)  # tools endpoint requires trailing slash
    existing = [t for t in (tools_data if isinstance(tools_data, list) else [])
                if t.get("name") == "AI Company Tools"]

    try:
        tool_content = open(TOOL_FILE, encoding="utf-8").read()
    except:
        print(f"  [!] Tool file not found: {TOOL_FILE}")
        tool_content = None

    if tool_content:
        tool_payload = {
            "id":          "ai_company_tools",
            "name":        "AI Company Tools",
            "content":     tool_content,
            "meta":        {"description": "Generate mockups and create projects"},
        }
        if existing:
            print("  Updating AI Company Tools (content may have changed)...")
            data, status = req("POST", "/api/v1/tools/id/ai_company_tools/update", tool_payload, token=token)
            if status in (200, 201):
                print("  [✓] Tool updated successfully!")
            else:
                print(f"  [!] Tool update failed ({status}): {str(data)[:150]}")
        else:
            print("  Uploading AI Company Tools...")
            data, status = req("POST", "/api/v1/tools/create", tool_payload, token=token)
            if status in (200, 201):
                print("  [✓] Tool uploaded successfully!")
            else:
                print(f"  [!] Tool upload failed ({status}): {str(data)[:150]}")

    # ── Create Project Manager model ─────────────────────────────
    print("  Creating Project Manager model...")
    try:
        sys_prompt = open(os.path.join(BASE_DIR, "tools-api", "system-prompt.md"),
                          encoding="utf-8").read()
    except:
        sys_prompt = "You are an AI Project Manager. Help clients build software applications."

    # جيب الموديل من config/models.json — وحوّله لـ LiteLLM alias الصحيح
    # (Open WebUI لا يعرف "provider/model" خام، فقط الـ aliases المعرّفة في litellm-config.yaml)
    PROVIDER_TO_ALIAS = {
        "anthropic": "claude",
        "openai":    "gpt",
        "openrouter":"openrouter-auto",
    }
    try:
        import json as _json
        models_path = os.environ.get("CONFIG_FILE", "/app/config/models.json")
        models_cfg = _json.loads(open(models_path).read())
        raw_model = models_cfg.get("manager", "")
        provider = raw_model.split("/", 1)[0] if "/" in raw_model else raw_model
        if provider == "openrouter":
            # litellm-config.yaml فيه wildcard "openrouter/*" — نمرّر السلسلة
            # الكاملة كما هي عشان يستخدم الموديل المحدّد فعليًا، لا alias عام
            base_model = raw_model
        else:
            base_model = PROVIDER_TO_ALIAS.get(provider, raw_model)
    except Exception as e:
        print(f"  [!] Could not read models config: {e}")
        base_model = ""

    if not base_model:
        print("  [!] No model configured for manager — set it in Dashboard → Models first")
        return 0

    model_payload = {
        "id": "ai_company_project_manager",
        "name": "🤖 مدير المشروع — AI Company",
        "base_model_id": base_model,
        "meta": {
            "description": "مدير مشاريع ذكاء اصطناعي — يحوّل أفكارك لتطبيقات حقيقية",
            "capabilities": {"tools": True},
            "toolIds": ["ai_company_tools"]
        },
        "params": {
            "system": sys_prompt,
            "temperature": 0.7
        },
        "access_grants": [],
        "is_active": True
    }

    # تحقق لو الموديل موجود بالفعل — لو موجود حدّثه، لو غير موجود أنشئه
    existing_models, _ = req("GET", "/api/v1/models", token=token)  # NO trailing slash — returns SPA HTML otherwise
    models_list = existing_models.get("data", []) if isinstance(existing_models, dict) else (existing_models if isinstance(existing_models, list) else [])
    model_exists = any(m.get("id") == "ai_company_project_manager" for m in models_list)

    if model_exists:
        model_data, model_status = req("POST", "/api/v1/models/model/update?id=ai_company_project_manager",
                                        model_payload, token=token)
        if model_status in (200, 201):
            print("  [✓] Project Manager model updated!")
        else:
            print(f"  [!] Model update failed ({model_status}): {str(model_data)[:100]}")
    else:
        model_data, model_status = req("POST", "/api/v1/models/create", model_payload, token=token)
        if model_status in (200, 201):
            print("  [✓] Project Manager model created!")
        else:
            print(f"  [!] Model creation failed ({model_status}): {str(model_data)[:100]}")

    # Save credentials to .env
    for k, v in [("WEBUI_ADMIN_EMAIL", admin_email),
                 ("WEBUI_ADMIN_PASSWORD", admin_password)]:
        cur = get_env(k)
        if not cur:
            with open(ENV_FILE, "a") as f:
                f.write(f"\n{k}={v}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
