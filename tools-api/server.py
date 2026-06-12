"""
Tool Calls API — خدمة الأدوات الخارجية
تربط Open WebUI بـ GitHub و OpenHands
"""
import os, json, urllib.request, urllib.error, re
from http.server import HTTPServer, BaseHTTPRequestHandler

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GIT_USERNAME  = os.environ.get("GIT_USERNAME", "")
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
PORT          = int(os.environ.get("PORT", "9000"))


def gh_request(method, path, data=None):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ai-company-tools")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code


def get_github_username():
    """جلب اسم المستخدم تلقائياً لو GIT_USERNAME فارغ"""
    if GIT_USERNAME:
        return GIT_USERNAME
    data, status = gh_request("GET", "/user")
    if status == 200:
        return data.get("login", "")
    return ""


def create_github_repo(name: str, description: str = "", private: bool = False):
    """إنشاء ريبو GitHub جديد"""
    if not GITHUB_TOKEN:
        return {"error": "GITHUB_TOKEN غير مضبوط"}

    safe_name = re.sub(r"[^a-zA-Z0-9\-]", "-", name.lower()).strip("-")
    username  = get_github_username()

    data, status = gh_request("POST", "/user/repos", {
        "name":        safe_name,
        "description": description,
        "private":     private,
        "auto_init":   True,
    })

    if status in (200, 201):
        return {
            "success":   True,
            "repo_url":  data.get("html_url"),
            "clone_url": data.get("clone_url"),
            "full_name": data.get("full_name"),
            "name":      safe_name,
        }

    # ريبو موجود مسبقاً
    if status == 422 and username:
        data2, s2 = gh_request("GET", f"/repos/{username}/{safe_name}")
        if s2 == 200:
            return {
                "success":   True,
                "repo_url":  data2.get("html_url"),
                "clone_url": data2.get("clone_url"),
                "full_name": data2.get("full_name"),
                "name":      safe_name,
                "note":      "ريبو موجود مسبقاً",
            }

    return {"error": f"فشل إنشاء الريبو ({status}): {data.get('message','')}"}


def start_coding_task(repo_full_name: str, task: str):
    """إرسال مهمة لـ OpenHands"""
    # الـ format الصح: initial_user_msg + رابط الريبو في نص المهمة
    full_task = task
    if repo_full_name:
        full_task = (f"Repository: https://github.com/{repo_full_name}\n\n"
                     f"Clone it and work on it locally.\n\n{task}")
    try:
        body = json.dumps({"initial_user_msg": full_task}).encode()
        req  = urllib.request.Request(
            f"{OPENHANDS_URL}/api/conversations",
            data=body, method="POST"
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.load(r)
            conv_id = resp.get("conversation_id") or resp.get("id")
            return {
                "success":         True,
                "conversation_id": conv_id,
                "openhands_url":   f"http://192.168.2.29:3000",
                "note":            f"تابع التقدم على: http://192.168.2.29:3000",
            }
    except Exception as e:
        return {
            "success":        False,
            "note":           "OpenHands يعمل — افتح الرابط وأعطه المهمة",
            "openhands_url":  "http://192.168.2.29:3000",
            "suggested_task": task,
            "error":          str(e)[:100],
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            username = get_github_username()
            self.send_json({"status": "ok", "github": bool(GITHUB_TOKEN), "username": username})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/create-repo":
            self.send_json(create_github_repo(
                name=body.get("name", "new-project"),
                description=body.get("description", ""),
                private=body.get("private", False),
            ))

        elif self.path == "/start-coding":
            self.send_json(start_coding_task(
                repo_full_name=body.get("repo_full_name", ""),
                task=body.get("task", ""),
            ))

        elif self.path == "/create-and-start":
            repo = create_github_repo(
                name=body.get("name", "new-project"),
                description=body.get("description", ""),
            )
            if not repo.get("success"):
                self.send_json(repo); return
            coding = start_coding_task(
                repo_full_name=repo.get("full_name", ""),
                task=body.get("task", ""),
            )
            self.send_json({**repo, "coding": coding})

        else:
            self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    username = get_github_username()
    print(f"[+] Tools API — البورت {PORT}")
    print(f"    GitHub: {'✓ ' + username if GITHUB_TOKEN else '✗ غير مضبوط'}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
