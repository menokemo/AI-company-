"""
Tool Calls API — خدمة الأدوات الخارجية
تربط Open WebUI بـ GitHub و OpenHands
"""
import os, json, subprocess, urllib.request, urllib.error
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


def create_github_repo(name: str, description: str = "", private: bool = False):
    """إنشاء ريبو GitHub جديد"""
    if not GITHUB_TOKEN:
        return {"error": "GITHUB_TOKEN غير مضبوط"}
    safe_name = name.lower().replace(" ", "-").replace("_", "-")
    data, status = gh_request("POST", "/user/repos", {
        "name": safe_name,
        "description": description,
        "private": private,
        "auto_init": True,
    })
    if status in (200, 201):
        return {
            "success": True,
            "repo_url": data.get("html_url"),
            "clone_url": data.get("clone_url"),
            "name": safe_name,
        }
    if status == 422:
        # الريبو موجود بالفعل
        data2, _ = gh_request("GET", f"/repos/{GIT_USERNAME}/{safe_name}")
        return {
            "success": True,
            "repo_url": data2.get("html_url"),
            "clone_url": data2.get("clone_url"),
            "name": safe_name,
            "note": "ريبو موجود مسبقاً",
        }
    return {"error": f"فشل إنشاء الريبو: {data}"}


def start_coding_task(repo_url: str, task: str):
    """إرسال مهمة لـ OpenHands عبر API"""
    try:
        payload = json.dumps({
            "task": task,
            "repository": repo_url,
        }).encode()
        req = urllib.request.Request(
            f"{OPENHANDS_URL}/api/conversations",
            data=payload, method="POST"
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.load(r)
            return {"success": True, "conversation_id": resp.get("id"), "url": OPENHANDS_URL}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "note": "OpenHands API غير متاحة — افتح OpenHands يدوياً وأعطه المهمة",
            "openhands_url": "http://192.168.2.29:3000",
            "task": task,
            "repo": repo_url,
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # تصاميت الـ logs

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
            self.send_json({"status": "ok", "github": bool(GITHUB_TOKEN)})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/create-repo":
            result = create_github_repo(
                name=body.get("name", "new-project"),
                description=body.get("description", ""),
                private=body.get("private", False),
            )
            self.send_json(result)

        elif self.path == "/start-coding":
            result = start_coding_task(
                repo_url=body.get("repo_url", ""),
                task=body.get("task", ""),
            )
            self.send_json(result)

        elif self.path == "/create-and-start":
            # إنشاء الريبو وتشغيل OpenHands دفعة واحدة
            repo = create_github_repo(
                name=body.get("name", "new-project"),
                description=body.get("description", ""),
            )
            if not repo.get("success"):
                self.send_json(repo); return
            coding = start_coding_task(
                repo_url=repo["repo_url"],
                task=body.get("task", ""),
            )
            self.send_json({**repo, "coding": coding})

        else:
            self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"[+] Tools API تعمل على البورت {PORT}")
    print(f"    GitHub token: {'✓' if GITHUB_TOKEN else '✗ غير مضبوط'}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
