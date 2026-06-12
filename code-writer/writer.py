"""
Code Writer Service
يستقبل وصف المشروع، يطلب من Claude كتابة الكود، ويرفعه على GitHub مباشرة.
"""
import os, json, base64, re, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
PORT              = int(os.environ.get("PORT", "9001"))

SYSTEM_PROMPT = """أنت مهندس برمجيات محترف. مهمتك كتابة كود كامل وجاهز للتشغيل.

عند استقبال طلب مشروع، أرجع JSON فقط بهذا الشكل (بدون أي نص خارج JSON):
{
  "files": [
    {"path": "index.html", "content": "..."},
    {"path": "style.css", "content": "..."},
    {"path": "README.md", "content": "..."}
  ],
  "description": "وصف قصير لما تم إنشاؤه"
}

قواعد:
- الكود كامل وقابل للتشغيل مباشرة
- README.md دائماً موجود
- لا تضع backticks أو markdown خارج الـ JSON
- محتوى الملفات كامل وليس placeholder"""


def call_claude(task: str) -> dict:
    """استدعاء Claude API لتوليد الكود"""
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY غير مضبوط"}

    payload = json.dumps({
        "model": "claude-sonnet-4-5",
        "max_tokens": 8192,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": task}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload, method="POST"
    )
    req.add_header("x-api-key", ANTHROPIC_API_KEY)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
        text = resp["content"][0]["text"].strip()
        # نظّف الـ JSON من أي markdown
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)[:200]}


def push_to_github(repo_full_name: str, files: list, commit_msg: str) -> dict:
    """رفع الملفات على GitHub عبر API"""
    if not GITHUB_TOKEN:
        return {"error": "GITHUB_TOKEN غير مضبوط"}

    pushed, failed = [], []
    for f in files:
        path    = f.get("path", "")
        content = f.get("content", "")
        encoded = base64.b64encode(content.encode()).decode()

        url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
        # جلب SHA الملف الحالي (لو موجود)
        sha = None
        try:
            r2 = urllib.request.Request(url)
            r2.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
            r2.add_header("Accept", "application/vnd.github+json")
            with urllib.request.urlopen(r2, timeout=10) as resp:
                sha = json.load(resp).get("sha")
        except urllib.error.HTTPError:
            pass

        body = {"message": commit_msg, "content": encoded}
        if sha:
            body["sha"] = sha

        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT")
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
        req.add_header("Accept",        "application/vnd.github+json")
        req.add_header("Content-Type",  "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                pushed.append(path)
        except urllib.error.HTTPError as e:
            failed.append(f"{path}: {e.code}")

    return {"pushed": pushed, "failed": failed}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json({
                "status": "ok",
                "claude": bool(ANTHROPIC_API_KEY),
                "github": bool(GITHUB_TOKEN)
            })
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        n    = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}

        if self.path == "/write-code":
            task            = body.get("task", "")
            repo_full_name  = body.get("repo_full_name", "")
            commit_msg      = body.get("commit_msg", "🤖 Initial project code")

            if not task:
                self.send_json({"error": "task مطلوب"}); return

            print(f"[+] توليد الكود: {task[:60]}...")
            result = call_claude(task)

            if "error" in result:
                self.send_json(result); return

            files       = result.get("files", [])
            description = result.get("description", "")
            print(f"[+] تم توليد {len(files)} ملف")

            push_result = {"pushed": [], "failed": [], "note": "لم يُحدَّد repo"}
            if repo_full_name:
                push_result = push_to_github(repo_full_name, files, commit_msg)
                print(f"[+] رُفع: {push_result['pushed']}")

            self.send_json({
                "success":     True,
                "files_count": len(files),
                "files":       [f["path"] for f in files],
                "description": description,
                "github":      push_result,
                "repo_url":    f"https://github.com/{repo_full_name}" if repo_full_name else None
            })

        else:
            self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"[+] Code Writer :{PORT}")
    print(f"    Claude: {'✓' if ANTHROPIC_API_KEY else '✗'}")
    print(f"    GitHub: {'✓' if GITHUB_TOKEN else '✗'}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
