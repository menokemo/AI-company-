import os, json, urllib.request, urllib.error, re
from http.server import HTTPServer, BaseHTTPRequestHandler

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
PORT          = int(os.environ.get("PORT", "9000"))

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
    msg = f"Repository: https://github.com/{full_name}\n\nClone it and complete this task:\n\n{task}"
    try:
        body = json.dumps({"initial_user_msg": msg}).encode()
        req = urllib.request.Request(f"{OPENHANDS_URL}/api/conversations", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.load(r)
            return {"success":True,"conversation_id":d.get("conversation_id"),"url":"http://192.168.2.29:3000"}
    except Exception as e:
        return {"success":False,"error":str(e)[:80],"openhands_url":"http://192.168.2.29:3000","task":task}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def json(self, d, s=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(s); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",len(b)); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(200); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()
    def do_GET(self):
        if self.path=="/health": self.json({"status":"ok","github":bool(GITHUB_TOKEN),"user":get_username()})
        else: self.json({"error":"not found"},404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0)); b = json.loads(self.rfile.read(n)) if n else {}
        if self.path=="/create-repo": self.json(create_repo(b.get("name","project"),b.get("description","")))
        elif self.path=="/start-coding": self.json(start_coding(b.get("full_name",""),b.get("task","")))
        elif self.path=="/create-and-start":
            r = create_repo(b.get("name","project"),b.get("description",""))
            if not r.get("success"): self.json(r); return
            c = start_coding(r.get("full_name",""),b.get("task",""))
            self.json({**r,"coding":c})
        else: self.json({"error":"not found"},404)

if __name__=="__main__":
    user = get_username()
    print(f"[+] Tools API :{PORT} — GitHub: {'✓ '+user if GITHUB_TOKEN else '✗'}")
    HTTPServer(("0.0.0.0",PORT),H).serve_forever()
