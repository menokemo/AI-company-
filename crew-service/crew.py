"""
crew.py — Pipeline رئيسي لـ CrewAI
HTTP Service يستقبل طلبات من tools-api ويشغّل الـ pipeline.
"""
import os, json, time, traceback, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from crewai import Crew, Process
from agents import make_agents
from tasks  import make_tasks

PORT          = int(os.environ.get("PORT", "9002"))
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")


def create_pr(repo_full_name: str, branch: str, title: str, body: str) -> dict:
    """إنشاء Pull Request على GitHub."""
    if not GITHUB_TOKEN:
        return {"error": "no GITHUB_TOKEN"}
    payload = json.dumps({
        "title": title,
        "body":  body,
        "head":  branch,
        "base":  "main",
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo_full_name}/pulls",
        data=payload, method="POST",
    )
    req.add_header("Authorization",  f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept",         "application/vnd.github+json")
    req.add_header("Content-Type",   "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            return {"success": True, "pr_url": d.get("html_url"), "pr_number": d.get("number")}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}


def start_openhands(repo_full_name: str, technical_plan: str) -> dict:
    """إرسال الخطة التقنية لـ OpenHands للتنفيذ."""
    msg = (
        f"Work on repository: {repo_full_name}\n\n"
        f"TECHNICAL PLAN (follow it exactly):\n\n{technical_plan}\n\n"
        f"After implementation:\n"
        f"1. git add -A\n"
        f"2. git commit -m \"feat: implement project\"\n"
        f"3. git push origin HEAD\n"
        f"Use $GITHUB_TOKEN if authentication needed."
    )
    payload = json.dumps({
        "initial_message": {"content": [{"type": "text", "text": msg}]},
        "selected_repository": repo_full_name,
        "git_provider": "github",
        "llm_model": "openai/claude",
    }).encode()
    req = urllib.request.Request(
        f"{OPENHANDS_URL}/api/v1/app-conversations",
        data=payload, method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
            return {
                "success": True,
                "conversation_id": d.get("id"),
                "status": d.get("status"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}


def run_pipeline(project: dict) -> dict:
    """
    يشغّل pipeline كامل:
    doc_analyzer → researcher → designer → planner → problem_solver → reviewer → OpenHands
    """
    start = time.time()
    result = {"project": project.get("name"), "stages": {}}

    try:
        # ── ١. إنشاء الـ agents والمهام ─────────────────────────────────
        agents = make_agents()
        tasks  = make_tasks(agents, project)

        # ── ٢. تشغيل الـ crew بشكل تسلسلي ─────────────────────────────
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
        )
        crew_output = crew.kickoff()

        # استخراج الخطة التقنية (output آخر مهمة قبل المراجعة = planner)
        plan_task_idx  = next(i for i, t in enumerate(tasks) if "planner" in t.agent.role.lower())
        technical_plan = tasks[plan_task_idx].output.raw if hasattr(tasks[plan_task_idx], 'output') else str(crew_output)

        result["stages"]["crew"] = {"success": True, "duration_s": round(time.time()-start)}

        # ── ٣. إرسال الخطة لـ OpenHands ──────────────────────────────────
        oh = start_openhands(project["repo_full_name"], technical_plan)
        result["stages"]["openhands"] = oh

        result["success"]      = oh.get("success", False)
        result["conversation_id"] = oh.get("conversation_id")
        result["full_output"]  = str(crew_output)[:3000]

    except Exception as e:
        result["success"] = False
        result["error"]   = str(e)
        result["trace"]   = traceback.format_exc()[-500:]

    result["total_duration_s"] = round(time.time() - start)
    return result


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def json_resp(self, d, status=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            agents = make_agents()
            self.json_resp({
                "status": "ok",
                "agents": list(agents.keys()),
                "models": {
                    k: os.environ.get(f"AGENT_{k.upper()}_MODEL", "claude")
                    for k in agents
                },
            })
        else:
            self.json_resp({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}

        if self.path == "/run-pipeline":
            result = run_pipeline(body)
            self.json_resp(result)

        elif self.path == "/create-pr":
            result = create_pr(
                body.get("repo_full_name", ""),
                body.get("branch", ""),
                body.get("title", "feat: project implementation"),
                body.get("body", ""),
            )
            self.json_resp(result)

        else:
            self.json_resp({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"[+] Crew Service :{PORT}")
    print(f"    Agents: doc_analyzer | researcher | designer | planner | problem_solver | reviewer")
    print(f"    OpenHands: {OPENHANDS_URL}")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
