import os, json, urllib.request, urllib.error, re
from http.server import HTTPServer, BaseHTTPRequestHandler

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
CREW_URL      = os.environ.get("CREW_URL",      "http://ai-crew:9002")
PORT          = int(os.environ.get("PORT", "9000"))
CONFIG_FILE   = os.environ.get("CONFIG_FILE", "/app/config/models.json")


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
                "url": f"http://192.168.2.29:3000",
                "conversation_url": f"http://192.168.2.29:3000/conversations/{conv_id}" if conv_id else None
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
        if self.path == "/config/models":
            self.json(read_config())
            return
        if self.path == "/health":
            self.json({"status":"ok","github":bool(GITHUB_TOKEN),"user":get_username(),"openhands_api":"v1"})
        else:
            self.json({"error":"not found"}, 404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0))
        b = json.loads(self.rfile.read(n)) if n else {}
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
