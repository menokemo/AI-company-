import os, json, urllib.request, urllib.error, re
from http.server import HTTPServer, BaseHTTPRequestHandler

def get_github_token() -> str:
    """يقرأ GITHUB_TOKEN من ملف .env مباشرة في كل استدعاء — لا نخزّنه كـ
    constant وقت بدء تشغيل الـ module، لأن 'Sync from Infisical' يكتب القيمة
    الجديدة في الملف فقط (بدون إعادة تشغيل tools-api نفسه)، فلو خزّناه هنا
    starup-time فقط، أي تحديث للتوكن بعد أول تشغيل لن يُستخدم أبداً."""
    install_dir = os.environ.get("INSTALL_DIR", "/opt/ai-company")
    env_file = os.path.join(install_dir, "infrastructure", ".env")
    try:
        for line in open(env_file, encoding="utf-8"):
            line = line.strip()
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")
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

    # نقرأ المفاتيح من ملف .env على القرص مباشرة، لا من os.environ المخزّنة
    # في ذاكرة الـ process وقت بدء التشغيل — لأن "Sync from Infisical" يكتب
    # القيم الجديدة في الملف فقط، ولا يعيد تشغيل tools-api نفسه (لتجنّب قتل
    # نفسه أثناء الرد على الطلب). فلو اعتمدنا على os.environ هنا، التحديثات
    # الجديدة (مفاتيح API المُضافة بعد أول تشغيل) لن تظهر أبداً حتى يُعاد
    # تشغيل الـ container بالكامل يدويًا.
    env = dict(os.environ)
    try:
        for line in open(ENV_FILE, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    except Exception:
        pass  # لو الملف غير موجود لأي سبب، نكتفي بـ os.environ كـ fallback

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
INSTALL_DIR   = os.environ.get("INSTALL_DIR", "/opt/ai-company")
ENV_FILE      = os.path.join(INSTALL_DIR, "infrastructure", ".env")
HOST_IP       = os.environ.get("HOST_IP", "localhost")


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
    GITHUB_TOKEN = get_github_token()
    if not GITHUB_TOKEN: return ""
    try:
        req = urllib.request.Request("https://api.github.com/user")
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r).get("login", "")
    except: return ""


def create_repo(name, description=""):
    GITHUB_TOKEN = get_github_token()
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


def check_project_status(name):
    """يتحقق من حالة مشروع حقيقية عبر GitHub مباشرة (المصدر الحقيقي للحقيقة)
    — كومتات حقيقية + Pull Requests، بدل الاعتماد على ذاكرة الموديل لمحادثة
    OpenHands القديمة التي ليس لديه أي وسيلة لمتابعتها."""
    GITHUB_TOKEN = get_github_token()
    if not GITHUB_TOKEN: return {"error": "GITHUB_TOKEN غير مضبوط"}
    safe = re.sub(r"[^a-zA-Z0-9\-]", "-", name.lower()).strip("-")
    user = get_username()
    full_name = f"{user}/{safe}"

    def gh(path):
        req = urllib.request.Request(f"https://api.github.com/repos/{full_name}{path}")
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)

    try:
        commits = gh("/commits?per_page=10")
    except urllib.error.HTTPError as e:
        return {"error": f"المشروع '{full_name}' غير موجود أو لم يتم إنشاؤه بعد ({e.code})"}

    only_initial = len(commits) <= 1
    try:
        prs = gh("/pulls?state=open")
    except Exception:
        prs = []

    return {
        "success": True,
        "full_name": full_name,
        "repo_url": f"https://github.com/{full_name}",
        "still_initializing": only_initial,
        "commit_count": len(commits),
        "recent_commits": [c["commit"]["message"] for c in commits[:5]],
        "open_pull_requests": [{"title": p["title"], "url": p["html_url"]} for p in prs],
    }


PROVIDER_TO_ALIAS = {
    "anthropic":  "claude",
    "openai":     "gpt",
    "openrouter": "openrouter-auto",
}

def get_coder_model():
    """يقرأ الموديل المختار لـ OpenHands من config/models.json (مفتاح 'coder')
    ويحوّله لـ LiteLLM alias الصحيح — بدل قيمة ثابتة (hardcoded)."""
    try:
        models_cfg = json.loads(open(CONFIG_FILE, encoding="utf-8").read())
        raw_model = models_cfg.get("coder", "")
        provider = raw_model.split("/", 1)[0] if "/" in raw_model else raw_model
        if provider == "openrouter":
            # litellm-config.yaml فيه wildcard "openrouter/*" — تمرير السلسلة
            # الكاملة يستخدم الموديل المحدّد فعليًا، لا alias عام يفقد الاختيار
            return f"openai/{raw_model}"
        alias = PROVIDER_TO_ALIAS.get(provider, "claude")
        return f"openai/{alias}"
    except Exception:
        return "openai/claude"


def _get_conversation_status(conv_id: str) -> dict:
    """يجيب حالة محادثة OpenHands الحالية."""
    req = urllib.request.Request(
        f"{OPENHANDS_URL}/api/v1/app-conversations/{conv_id}", method="GET"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _create_oh_conversation(payload: dict) -> dict:
    """نداء واحد لإنشاء محادثة في OpenHands."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OPENHANDS_URL}/api/v1/app-conversations",
        data=body, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def start_coding(full_name, task, description="", document_content=""):
    """إرسال مهمة لـ OpenHands V1 API.

    إعادة محاولة تلقائية: OpenHands V1 له مشكلة معروفة (race condition وقت
    إقلاع الـ sandbox container — راجع GitHub Issue #12500) تجعله أحياناً
    يدخل 'error state' فقط لأن فحص الجاهزية حصل قبل اكتمال الإقلاع بثوانٍ
    قليلة، بينما الـ sandbox نفسه سليم تماماً. نتحقق من الحالة بعد إنشاء
    المحادثة، ولو ظهر الخطأ المؤقت ده، نعيد المحاولة بمحادثة جديدة (حتى ٢
    محاولات إضافية) قبل الإفادة بالفشل للمستخدم.
    """
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
        "llm_model": get_coder_model(),
    }

    import time as _time
    last_error = None
    for attempt in range(3):  # محاولة أولى + ٢ إعادة محاولة
        try:
            d = _create_oh_conversation(payload)
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.read().decode()[:200]}"
            continue
        except Exception as e:
            last_error = str(e)[:150]
            continue

        conv_id = d.get("id") or d.get("conversation_id")
        if not conv_id:
            last_error = "لم يرجع OpenHands conversation_id"
            continue

        # نتحقق بسرعة لو الـ sandbox دخل 'error state' المؤقت المعروف
        status = d.get("status")
        for _ in range(6):  # ~12 ثانية فحص قصير
            if status != "ERROR":
                break
            _time.sleep(2)
            try:
                d2 = _get_conversation_status(conv_id)
                status = d2.get("status", status)
            except Exception:
                break

        if status == "ERROR":
            last_error = f"Sandbox entered error state (محاولة {attempt + 1}/3)"
            continue  # إعادة المحاولة بمحادثة جديدة

        return {
            "success": True,
            "conversation_id": conv_id,
            "status": status,
            "url": f"http://{HOST_IP}:3000",
            "conversation_url": f"http://{HOST_IP}:3000/conversations/{conv_id}"
        }

    return {"success": False, "error": last_error or "فشل غير معروف بعد 3 محاولات"}


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
        if self.path == "/config/prompts":
            try:
                pf = CONFIG_FILE.replace("models.json","agent-prompts.json")
                self.json(json.loads(open(pf).read()))
            except Exception as e:
                self.json({"error": str(e)})
            return
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
        if self.path == "/run-history":
            # سجل أعمال الموظفين (الـ 6 agents + OpenHands) — يُكتب من
            # crew-service على نفس volume الإعدادات المشترك /app/config
            history_file = os.path.join(os.path.dirname(CONFIG_FILE), "run_history.json")
            try:
                history = json.loads(open(history_file, encoding="utf-8").read())
            except Exception:
                history = []
            self.json({"history": history})
            return
        if self.path.startswith("/system/health"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            port = qs.get("port", [""])[0]
            proto = qs.get("proto", ["http"])[0]
            ok = False
            try:
                import socket
                s_ = socket.create_connection(("localhost", int(port)), timeout=2)
                s_.close()
                ok = True
            except Exception:
                ok = False
            self.json({"port": port, "up": ok})
            return
        if self.path == "/system/credentials":
            env = dict(os.environ)
            # قراءة من .env أيضاً
            try:
                for line in open(ENV_FILE):
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
            self.json({"status":"ok","github":bool(get_github_token()),"user":get_username(),"openhands_api":"v1"})
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
                host_ip = os.environ.get("HOST_IP", "localhost")
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
        if self.path == "/config/prompts":
            try:
                pf = CONFIG_FILE.replace("models.json","agent-prompts.json")
                existing = json.loads(open(pf).read()) if os.path.exists(pf) else {}
                for k,v in b.items():
                    if k in existing: existing[k]["prompt"] = v
                open(pf,"w",encoding="utf-8").write(json.dumps(existing, ensure_ascii=False, indent=2))
                self.json({"success":True})
            except Exception as e: self.json({"success":False,"error":str(e)})
            return
        if self.path == "/system/sync":
            import subprocess
            try:
                # قراءة أحدث قيم من .env مباشرةً — بدون cache
                env = os.environ.copy()
                try:
                    for line in open(ENV_FILE):
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, _, v = line.partition("=")
                            if v: env[k.strip()] = v.strip()
                except: pass
                sync_script = os.path.join(INSTALL_DIR, "secrets-sync", "infisical-sync.sh")
                r2 = subprocess.run(
                    ["/bin/bash", sync_script],
                    capture_output=True, text=True, timeout=300, env=env
                )
                out = (r2.stdout + r2.stderr).strip()
                self.json({"success": r2.returncode == 0, "output": out[-2000:]})
            except Exception as e:
                self.json({"success": False, "error": str(e)})
            return

        if self.path == "/setup/project-manager":
            try:
                import subprocess
                env = os.environ.copy()
                try:
                    for line in open(ENV_FILE):
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, _, v = line.partition("=")
                            if v: env[k.strip()] = v.strip()
                except: pass
                script_path = os.path.join(
                    os.path.dirname(ENV_FILE).replace("infrastructure", "secrets-sync"),
                    "setup-openwebui.py"
                )
                # استدعاء مباشر بدون "bash -c" — الالتفاف عبر shell إضافي يمكن
                # أن يمنع subprocess.run's timeout من قتل العملية الحقيقية
                # بشكل موثوق (يُنهي bash نفسه لكن قد يترك python3 يتيمًا).
                r2 = subprocess.run(
                    ["python3", script_path],
                    capture_output=True, text=True, timeout=90, env=env
                )
                out = (r2.stdout + r2.stderr).strip()
                self.json({"success": "Project Manager" in out or r2.returncode == 0, "output": out[-500:]})
            except Exception as e:
                self.json({"success": False, "error": str(e)})
            return
        if self.path == "/system/configure":
            import re
            allowed = {"INFISICAL_CLIENT_ID","INFISICAL_CLIENT_SECRET","INFISICAL_PROJECT_ID",
                       "GIT_USERNAME","GITHUB_TOKEN","ANTHROPIC_API_KEY",
                       "OPENAI_API_KEY","OPENROUTER_API_KEY","AGENT_SERVER_IMAGE_TAG"}
            saved = []
            env_file = ENV_FILE
            for key, val in b.items():
                if key in allowed and val:
                    try:
                        content = open(env_file).read()
                        pattern = "^" + key + "="
                        if re.search(pattern, content, re.MULTILINE):
                            content = re.sub(pattern + ".*", key + "=" + val, content, flags=re.MULTILINE)
                        else:
                            content = content.rstrip() + "\n" + key + "=" + val + "\n"
                        open(env_file, "w").write(content)
                        os.environ[key] = val
                        saved.append(key)
                    except Exception as e:
                        pass
            self.json({"success": bool(saved), "saved": saved})
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
        elif self.path == "/project-status":
            self.json(check_project_status(b.get("name","")))
        else:
            self.json({"error":"not found"}, 404)


if __name__ == "__main__":
    user = get_username()
    print(f"[+] Tools API :{PORT} — GitHub: {'✓ '+user if get_github_token() else '✗'} — OpenHands V1 API")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
