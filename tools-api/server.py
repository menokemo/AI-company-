import os, json, urllib.request, urllib.error, re
from http.server import HTTPServer, BaseHTTPRequestHandler

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
CREW_URL      = os.environ.get("CREW_URL",      "http://ai-crew:9002")
MOCKUPS_DIR   = os.environ.get("MOCKUPS_DIR", "/app/config/mockups")
import pathlib, uuid as _uuid
pathlib.Path(MOCKUPS_DIR).mkdir(parents=True, exist_ok=True)

def save_mockup(html: str, project: str, style: str, mid: int) -> str:
    """يحفظ الـ mockup ويرجع الـ ID."""
    mock_id = f"{_uuid.uuid4().hex[:8]}"
    data = {"id": mock_id, "project": project, "style": style, "num": mid}
    pathlib.Path(f"{MOCKUPS_DIR}/{mock_id}.html").write_text(html, encoding="utf-8")
    pathlib.Path(f"{MOCKUPS_DIR}/{mock_id}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return mock_id

_providers_cache = {"data": {}, "ts": 0}

# المزوّدون المعروفون مع endpoints الخاصة بهم
# الأسماء مش secret — هي الـ standard litellm provider IDs
_KNOWN_PROVIDERS = {
    "anthropic":  {"label":"Anthropic 🟠","url":"https://api.anthropic.com/v1/models","headers_fn":lambda k:{"x-api-key":k,"anthropic-version":"2023-06-01"},"data_path":"data"},
    "openai":     {"label":"OpenAI 🟢",   "url":"https://api.openai.com/v1/models",  "headers_fn":lambda k:{"Authorization":"Bearer "+k},"data_path":"data"},
    "openrouter": {"label":"OpenRouter 🔵","url":"https://openrouter.ai/api/v1/models","headers_fn":lambda k:{"Authorization":"Bearer "+k},"data_path":"data"},
}

def _fetch_models_from_url(url: str, headers: dict, data_path: str = "data", id_field: str = "id") -> list:
    req = urllib.request.Request(url)
    for k, v in headers.items(): req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.load(r)
        items = data.get(data_path, data) if isinstance(data, dict) else data
        return [m[id_field] for m in items if isinstance(m, dict) and id_field in m]

def get_available_providers(force_refresh: bool = False) -> dict:
    """
    يكتشف المزوّدين تلقائياً من env:
    - أي *_API_KEY موجود وطويل → يجيب موديلاته
    - إذا لم يُهيَّأ → يعرضه كـ 'not_configured' مع رسالة
    """
    import time
    global _providers_cache
    if not force_refresh and _providers_cache["data"] and (time.time() - _providers_cache["ts"]) < 3600:
        return _providers_cache["data"]

    env = dict(os.environ)
    result = {}

    for provider_id, info in _KNOWN_PROVIDERS.items():
        env_key = provider_id.upper() + "_API_KEY"
        key_val = env.get(env_key, "")
        if len(key_val) > 10:
            try:
                models = _fetch_models_from_url(
                    info["url"], info["headers_fn"](key_val), info["data_path"]
                )
                # تصفية موديلات OpenAI غير النصية
                if provider_id == "openai":
                    models = [m for m in models if not any(
                        x in m for x in ["embedding","whisper","dall-e","tts-","babbage","davinci","ada"]
                    )]
                result[provider_id] = {
                    "label": info["label"],
                    "models": sorted(models, reverse=True),
                    "count": len(models),
                    "configured": True,
                }
            except Exception as e:
                result[provider_id] = {
                    "label": info["label"], "models": [], "count": 0,
                    "configured": True, "error": str(e),
                }
        else:
            # مش مُهيَّأ — اعرضه مع رسالة للمستخدم
            result[provider_id] = {
                "label": info["label"], "models": [], "count": 0,
                "configured": False,
                "message": f"أضف {env_key} في Infisical ثم شغّل sync",
            }

    _providers_cache = {"data": result, "ts": time.time()}
    return result


PORT          = int(os.environ.get("PORT", "9000"))
CONFIG_FILE   = os.environ.get("CONFIG_FILE", "/app/config/models.json")
HOST_IP       = os.environ.get("HOST_IP", "192.168.2.29")


def read_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def write_config(data: dict) -> bool:
    try:
        # احتفظ بـ _comment
        existing = read_config()
        existing.update({k: v for k, v in data.items() if not k.startswith("_")})
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("write_config error:", e)
        return False


def get_username():
    if not GITHUB_TOKEN: return ""
    try:
        req = urllib.request.Request("https://api.github.com/user")
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r).get("login", "")
    except: return ""


def create_repo(name, description=""):
    if not GITHUB_TOKEN: return {"error": "GITHUB_TOKEN غير مضبوط"}
    safe = re.sub(r"[^a-zA-Z0-9\-]", "-", name.lower()).strip("-")
    body = json.dumps({"name":safe,"description":description,"auto_init":True}).encode()
    req = urllib.request.Request("https://api.github.com/user/repos", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            return {"success":True,"repo_url":d.get("html_url"),"full_name":d.get("full_name"),"name":safe}
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        if e.code == 422:
            user = get_username()
            req2 = urllib.request.Request(f"https://api.github.com/repos/{user}/{safe}")
            req2.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
            req2.add_header("Accept", "application/vnd.github+json")
            try:
                with urllib.request.urlopen(req2, timeout=10) as r:
                    d = json.load(r)
                    return {"success":True,"repo_url":d.get("html_url"),"full_name":d.get("full_name"),"name":safe,"note":"موجود مسبقاً"}
            except: pass
        return {"error": f"GitHub error {e.code}: {err.get('message','')}"}


def start_coding(full_name, task):
    """إرسال مهمة لـ OpenHands V1 API"""
    msg = (
        f"Work on this GitHub repository: {full_name}\n\n"
        f"The repository is already cloned in your workspace. "
        f"Complete the following task, then commit and push:\n\n"
        f"{task}\n\n"
        f"After completing the task:\n"
        f"1. git add -A\n"
        f"2. git commit -m \"feat: complete task\"\n"
        f"3. git push origin main\n"
        f"If push fails due to auth, configure: "
        f"git remote set-url origin https://$GITHUB_TOKEN@github.com/{full_name}.git"
    )
    payload = {
        "initial_message": {
            "content": [{"type": "text", "text": msg}]
        },
        "selected_repository": full_name,
        "git_provider": "github",
        "selected_branch": "main",
        "llm_model": "openai/claude",
    }
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OPENHANDS_URL}/api/v1/app-conversations",
            data=body, method="POST"
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            conv_id = d.get("id") or d.get("conversation_id")
            return {
                "success": True,
                "conversation_id": conv_id,
                "status": d.get("status"),
                "url": f"http://{HOST_IP}:3000",
                "conversation_url": f"http://{HOST_IP}:3000/conversations/{conv_id}" if conv_id else None
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {"success": False, "error": f"HTTP {e.code}: {err_body[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def json(self, d, s=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(s)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(b))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        if self.path.startswith("/mockups/"):
            mock_id = self.path.split("/mockups/")[1].rstrip("/")
            html_file = pathlib.Path(f"{MOCKUPS_DIR}/{mock_id}.html")
            if html_file.exists():
                b = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length", len(b))
                self.end_headers(); self.wfile.write(b)
            else:
                self.json({"error":"mockup not found"},404)
            return
        if self.path == "/mockups":
            files = list(pathlib.Path(MOCKUPS_DIR).glob("*.json"))
            mocks = []
            for f in sorted(files, reverse=True)[:20]:
                try: mocks.append(json.loads(f.read_text()))
                except: pass
            self.json({"mockups": mocks}); return
        if self.path.startswith("/config/providers"):
            force = "refresh" in self.path
            self.json(get_available_providers(force_refresh=force))
            return
        if self.path == "/config/models":
            self.json(read_config())
            return
        if self.path == "/system/configure":
            # يحفظ أي key=value في .env
            allowed = {"INFISICAL_CLIENT_ID","INFISICAL_CLIENT_SECRET","INFISICAL_PROJECT_ID",
                       "GIT_USERNAME","GITHUB_TOKEN","ANTHROPIC_API_KEY",
                       "OPENAI_API_KEY","OPENROUTER_API_KEY","AGENT_SERVER_IMAGE_TAG"}
            saved = []
            for key, val in b.items():
                if key in allowed and val:
                    # update .env
                    import re
                    env_file = "/opt/ai-company/infrastructure/.env"
                    try:
                        content = open(env_file).read()
                        pattern = "^" + key + "="
                        if re.search(pattern, content, re.MULTILINE):
                            content = re.sub(pattern + ".*", key + "=" + val, content, flags=re.MULTILINE)
                        else:
                            content = content.rstrip() + "\n" + key + "=" + val + "\n"
                        # update running container env
                        os.environ[key] = val
                        saved.append(key)
                    except Exception as e:
                        pass
            self.json({"success": bool(saved), "saved": saved})
            return
        if self.path == "/system/sync":
            import subprocess
            try:
                r2 = subprocess.run(
                    ["bash", "/opt/ai-company/secrets-sync/infisical-sync.sh"],
                    capture_output=True, text=True, timeout=120
                )
                out = (r2.stdout + r2.stderr).strip()
                self.json({"success": r2.returncode == 0, "output": out[-2000:]})
            except Exception as e:
                self.json({"success": False, "error": str(e)})
            return
        if self.path == "/system/credentials":
            env = dict(os.environ)
            # قراءة من .env أيضاً
            try:
                for line in open("/opt/ai-company/infrastructure/.env"):
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k,_,v = line.partition("=")
                        if v: env[k.strip()] = v.strip()
            except: pass
            host = env.get("HOST_IP", "localhost")
            self.json({
                "open_webui": {
                    "url":      f"http://{host}:8888",
                    "email":    env.get("WEBUI_ADMIN_EMAIL", "— not set —"),
                    "password": env.get("WEBUI_ADMIN_PASSWORD", "— not set —"),
                },
                "infisical": {
                    "url":      f"http://{host}:8080",
                    "email":    env.get("INFISICAL_ADMIN_EMAIL", "admin@ai-company.local"),
                    "password": env.get("INFISICAL_ADMIN_PASSWORD", "— not set —"),
                },
                "litellm": {
                    "url":       f"http://{host}:4000",
                    "master_key": env.get("LITELLM_MASTER_KEY","")[:30] + "...",
                },
                "portainer": {
                    "url": f"https://{host}:9443",
                },
            })
            return
        if self.path == "/health":
            self.json({"status":"ok","github":bool(GITHUB_TOKEN),"user":get_username(),"openhands_api":"v1"})
        else:
            self.json({"error":"not found"}, 404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0))
        b = json.loads(self.rfile.read(n)) if n else {}
        if self.path == "/generate-mockups":
            # استدعاء crew-service لتوليد ٣ تصميمات
            try:
                body2 = json.dumps(b).encode()
                req2 = urllib.request.Request(f"{CREW_URL}/design-options",data=body2,method="POST")
                req2.add_header("Content-Type","application/json")
                with urllib.request.urlopen(req2, timeout=180) as r2:
                    result = json.load(r2)
                # حفظ الـ mockups
                host_ip = os.environ.get("HOST_IP","192.168.2.29")
                saved = []
                for m in result.get("mockups",[]):
                    mid = save_mockup(m["html"], b.get("name",""), m["style"], m["id"])
                    saved.append({
                        "id": m["id"], "mock_id": mid,
                        "style": m.get("style_ar", m["style"]),
                        "url": f"http://{host_ip}:9000/mockups/{mid}",
                    })
                self.json({"success":True,"mockups":saved,"project":b.get("name","")})
            except Exception as e:
                self.json({"success":False,"error":str(e)})
            return
        if self.path == "/config/models":
            if write_config(b):
                self.json({"success": True, "config": read_config()})
            else:
                self.json({"success": False, "error": "فشل الحفظ"}, 500)
            return
        if self.path == "/config/restart":
            svc = b.get("service", "")
            import subprocess
            try:
                subprocess.run(["docker","restart",f"ai-{svc}"], timeout=10, check=True, capture_output=True)
                self.json({"success": True, "message": f"تمت إعادة تشغيل {svc}"})
            except Exception as e:
                self.json({"success": False, "error": str(e)})
            return
        if self.path == "/create-repo":
            self.json(create_repo(b.get("name","project"), b.get("description","")))
        elif self.path == "/start-coding":
            self.json(start_coding(b.get("full_name",""), b.get("task","")))
        elif self.path == "/create-and-start":
            r = create_repo(b.get("name","project"), b.get("description",""))
            if not r.get("success"): self.json(r); return
            c = start_coding(r.get("full_name",""), b.get("task",""), b.get("description",""), b.get("document_content",""))
            self.json({**r, "coding": c})
        else:
            self.json({"error":"not found"}, 404)


if __name__ == "__main__":
    user = get_username()
    print(f"[+] Tools API :{PORT} — GitHub: {'✓ '+user if GITHUB_TOKEN else '✗'} — OpenHands V1 API")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
