"""
crew.py — HTTP Service للـ multi-agent pipeline.
"""
import os, json, time, traceback, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pipeline import run_pipeline

PROVIDER_TO_ALIAS = {"anthropic": "claude", "openai": "gpt", "openrouter": "openrouter-auto"}

def get_coder_model():
    """يقرأ الموديل المختار لـ OpenHands من config/models.json (مفتاح 'coder')."""
    try:
        cfg = json.loads(open(os.environ.get("CONFIG_FILE", "/app/config/models.json")).read())
        raw = cfg.get("coder", "")
        provider = raw.split("/", 1)[0] if "/" in raw else raw
        return f"openai/{PROVIDER_TO_ALIAS.get(provider, 'claude')}"
    except Exception:
        return "openai/claude"

PORT          = int(os.environ.get("PORT", "9002"))
HISTORY_FILE  = os.environ.get("HISTORY_FILE", "/app/config/run_history.json")
CURRENT_RUN   = {"running": False, "project": "", "current": "", "done": []}

def _load_history() -> list:
    """يحمّل سجل التشغيلات السابقة من ملف على القرص (ينجو من إعادة تشغيل الـ container)."""
    try:
        return json.load(open(HISTORY_FILE, encoding="utf-8"))
    except Exception:
        return []

def _save_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(RUN_HISTORY[-200:], f, ensure_ascii=False)  # حد أقصى 200 تشغيلة
    except Exception as e:
        print(f"[!] فشل حفظ سجل التشغيلات: {e}")

RUN_HISTORY = _load_history()   # سجل pipeline runs — محفوظ على القرص
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
def get_github_token() -> str:
    """يقرأ GITHUB_TOKEN من ملف .env مباشرة في كل استدعاء — لا constant ثابت
    وقت بدء التشغيل، لأن sync بيحدّث الملف بدون إعادة تشغيل الخدمة."""
    env_file = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")
    try:
        for line in open(env_file, encoding="utf-8"):
            line = line.strip()
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")


def create_pr(repo: str, branch: str, title: str, body: str) -> dict:
    GITHUB_TOKEN = get_github_token()
    if not GITHUB_TOKEN:
        return {"error": "no GITHUB_TOKEN"}
    payload = json.dumps({
        "title": title, "body": body, "head": branch, "base": "main",
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls",
        data=payload, method="POST",
    )
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept",        "application/vnd.github+json")
    req.add_header("Content-Type",  "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            return {"success": True, "pr_url": d.get("html_url"), "pr_number": d.get("number")}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}


def start_openhands(repo: str, plan: str) -> dict:
    msg = (
        f"Work on repository: {repo}\n\n"
        f"TECHNICAL PLAN — implement exactly:\n\n{plan}\n\n"
        f"After implementation:\n"
        f"1. git add -A\n"
        f"2. git commit -m 'feat: implement project'\n"
        f"3. git push origin HEAD\n"
        f"Use $GITHUB_TOKEN if auth needed."
    )
    payload = json.dumps({
        "initial_message": {"content": [{"type": "text", "text": msg}]},
        "selected_repository": repo,
        "git_provider": "github",
        "llm_model": get_coder_model(),
    }).encode()
    req = urllib.request.Request(
        f"{OPENHANDS_URL}/api/v1/app-conversations",
        data=payload, method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            return {"success": True, "conversation_id": d.get("id"), "status": d.get("status")}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}


def full_pipeline(project: dict) -> dict:
    global CURRENT_RUN
    start  = time.time()
    name   = project.get("name", "مشروع")
    result = {"project": name, "stages": {}}

    CURRENT_RUN = {"running": True, "project": name, "current": "doc_analyzer", "done": []}

    try:
        crew_result = run_pipeline(project, status_cb=lambda stage: _update_status(stage))
        result["stages"]     = {k: (v[:1500] + ("..." if len(v) > 1500 else "")) for k, v in crew_result["stages"].items()}
        result["stages"]["_crew_ok"] = True

        CURRENT_RUN["current"] = "openhands"
        oh = start_openhands(project["repo_full_name"], crew_result["final_plan"])
        result["stages"]["openhands"] = oh
        result["success"]         = oh.get("success", False)
        result["conversation_id"] = oh.get("conversation_id")
        result["conversation_url"] = f"http://{os.environ.get("HOST_IP","localhost")}:3000/conversations/{oh.get("conversation_id")}" if oh.get("conversation_id") else None
    except Exception as e:
        result["success"] = False
        result["error"]   = str(e)
        result["trace"]   = traceback.format_exc()[-500:]

    result["duration_s"] = round(time.time() - start)
    result["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    CURRENT_RUN = {"running": False, "project": "", "current": "", "done": []}
    RUN_HISTORY.append(result)
    _save_history()
    return result

def _update_status(stage: str):
    global CURRENT_RUN
    if CURRENT_RUN["current"]:
        CURRENT_RUN["done"].append(CURRENT_RUN["current"])
    CURRENT_RUN["current"] = stage


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def json_resp(self, d, s=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(s)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/run-status":
            import copy
            resp = copy.copy(CURRENT_RUN)
            resp["history"] = RUN_HISTORY[-20:]
            self.json_resp(resp)
            return
        if self.path == "/" or self.path == "/status" or self.path == "/ui":
            # serve ui.html
            import pathlib
            ui_file = pathlib.Path("/app/ui.html")
            if ui_file.exists():
                b = ui_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length", len(b))
                self.end_headers()
                self.wfile.write(b)
            else:
                self.json_resp({"error":"ui.html not found"}, 404)
            return
        if self.path == "/status-json":
            agents_models = {
                a: os.environ.get(f"AGENT_{a.upper()}_MODEL", "claude")
                for a in ["doc_analyzer","researcher","designer","planner","problem_solver","reviewer"]
            }
            icons = {"doc_analyzer":"📄","researcher":"🔍","designer":"🎨","planner":"📋","problem_solver":"🔧","reviewer":"👁️"}
            arabic = {"doc_analyzer":"محلل نصوص","researcher":"باحث","designer":"مصمم","planner":"مخطط","problem_solver":"حلّال مشاكل","reviewer":"مراجع"}
            rows = "".join(f'<tr><td>{icons[a]} {arabic[a]}</td><td><code>{m}</code></td></tr>' for a,m in agents_models.items())
            html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
<title>Crew Pipeline</title>
<style>body{{font-family:Arial,sans-serif;background:#0d1117;color:#e6edf3;padding:30px;}}
h1{{color:#6c8fff;}}table{{width:100%;border-collapse:collapse;margin-top:20px;}}
th,td{{padding:12px;border:1px solid #30363d;text-align:right;}}
th{{background:#161b22;}}code{{color:#79c0ff;background:#0d1117;padding:2px 6px;border-radius:4px;}}
.ok{{color:#3fb950;font-weight:bold;}}</style></head>
<body><h1>👥 Crew Pipeline</h1>
<p class="ok">● شغّال</p>
<h3>الموظفون والموديلات</h3>
<table><tr><th>الموظف</th><th>الموديل</th></tr>{rows}</table>
<p style="color:#8b949e;margin-top:20px;font-size:13px;">Pipeline تسلسلي — 6 agents — LiteLLM</p>
</body></html>"""
            b = html.encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length", len(b))
            self.end_headers()
            self.wfile.write(b)
            return
        if self.path == "/health":
            import json as _j
            try:
                cfg = _j.load(open(os.environ.get("CONFIG_FILE","/app/config/models.json")))
            except: cfg = {}
            self.json_resp({
                "status": "ok",
                "agents": ["doc_analyzer","researcher","designer","planner","problem_solver","reviewer"],
                "models": {a: cfg.get(a,"claude") for a in ["doc_analyzer","researcher","designer","planner","problem_solver","reviewer"]},
                "openhands": OPENHANDS_URL,
            })
        else:
            self.json_resp({"error": "not found"}, 404)

    def do_POST(self):
        n    = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        if   self.path == "/run-pipeline":    self.json_resp(full_pipeline(body))
        elif self.path == "/create-pr":       self.json_resp(create_pr(body.get("repo_full_name",""), body.get("branch",""), body.get("title","feat: project"), body.get("body","")))
        elif self.path == "/design-options":  self.json_resp(generate_design_options(body))
        else:                                 self.json_resp({"error": "not found"}, 404)


def generate_design_options(project: dict) -> dict:
    """يولّد 3 تصميمات HTML مختلفة."""
    name         = project.get("name", "project")
    description  = project.get("description", "")
    requirements = project.get("requirements", "")
    LITELLM_URL  = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")
    LITELLM_KEY  = os.environ.get("LITELLM_API_KEY", "")
    try:
        with open(os.environ.get("CONFIG_FILE", "/app/config/models.json")) as f:
            import json as _j; cfg = _j.load(f)
    except: cfg = {}
    model = cfg.get("designer", "claude")

    styles = [
        ("modern",       "Modern & Minimal",   "#6366f1", "#f8fafc"),
        ("vibrant",      "Vibrant & Bold",     "#f59e0b", "#0f172a"),
        ("professional", "Professional SaaS",  "#0ea5e9", "#ffffff"),
    ]

    def call_llm(model_str, prompt_text):
        import requests as _r, time as _t
        msgs = [{"role": "user", "content": prompt_text}]
        if "/" in model_str:
            import litellm
            last_exc = None
            for _attempt in range(3):
                try:
                    resp = litellm.completion(
                        model=model_str, messages=msgs,
                        max_tokens=4096, temperature=0.7,
                    )
                    return resp.choices[0].message.content
                except litellm.RateLimitError as _e:
                    # موديلات OpenRouter المجانية (":free") كثيراً ما تُرفض
                    # مؤقتاً بـ rate-limit — إعادة محاولة بعد انتظار قصير
                    last_exc = _e
                    _t.sleep(9)
                    continue
            raise last_exc
        else:
            lurl = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")
            lkey = os.environ.get("LITELLM_API_KEY", "")
            r = _r.post(lurl + "/v1/chat/completions",
                headers={"Authorization": "Bearer " + lkey, "Content-Type": "application/json"},
                json={"model": model_str, "messages": msgs, "max_tokens": 4096},
                timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


    mockups = []
    for i, (style_key, style_name, accent, bg) in enumerate(styles, 1):
        prompt = """You are a world-class UI/UX designer creating a Figma-quality prototype.

PROJECT: """ + name + """
DESCRIPTION: """ + description + """
REQUIREMENTS: """ + requirements + """
STYLE: """ + style_name + """ (accent: """ + accent + """, background: """ + bg + """)

Create a complete single-file HTML prototype with:

1. TAILWIND CSS from CDN (https://cdn.tailwindcss.com)
2. MULTIPLE SCREENS (4-5 screens): dashboard, detail view, form, list, settings
3. SIDEBAR NAVIGATION with icons (use unicode or inline SVG)
4. CLICK NAVIGATION between screens (JavaScript showScreen function)
5. REALISTIC CONTENT with actual data relevant to the project
6. DESIGN SYSTEM: consistent colors, typography, spacing throughout
7. COMPONENTS: cards, tables, charts (CSS only), badges, buttons, modals
8. DARK/LIGHT theme based on style

STRUCTURE:
- Header with logo + user avatar
- Sidebar with navigation items (each links to a screen)
- Main content area (changes per screen)
- Each screen has realistic data and interactions

REQUIREMENTS:
- Mobile responsive
- Smooth transitions between screens
- Hover states on all interactive elements
- Loading states where appropriate
- Empty states for lists
- Form validation visual feedback

Return ONLY the complete HTML file. No explanations."""
        try:
            html = call_llm(model, prompt)
            if "```html" in html:
                html = html.split("```html")[1].split("```")[0].strip()
            elif "```" in html:
                html = html.split("```")[1].split("```")[0].strip()
        except Exception as e:
            html = "<h1>Error: " + str(e) + "</h1>"
        mockups.append({"id": i, "style": style_key, "style_ar": style_name, "html": html})

    return {"success": True, "mockups": mockups, "project": name}




if __name__ == "__main__":
    print(f"[+] Crew Service :{PORT} — 6 agents — no external framework")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
