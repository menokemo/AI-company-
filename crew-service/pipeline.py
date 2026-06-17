"""
pipeline.py — Multi-agent pipeline بدون crewai.
كل agent = LLM call منفصل بـ context من الـ agent السابق.
"""
import os, json, requests, time


CONFIG_FILE = os.environ.get("CONFIG_FILE", "/app/config/models.json")

def _model(agent_key: str, default: str = "claude") -> str:
    """يقرأ الموديل المختار لهذا الـ agent من config/models.json
    (المفتاح نفسه اللي بيحفظه المستخدم من لوحة التحكم)."""
    try:
        cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
        return cfg.get(agent_key) or default
    except Exception:
        return default

def _read_api_keys() -> dict:
    """يقرأ API keys من env — مُحقَنة من docker-compose/Infisical."""
    return dict(os.environ)


PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "agent-prompts.json")

def _agent_prompt(key: str, default: str = "") -> str:
    """يقرأ الـ prompt من agent-prompts.json أو يرجع الـ default."""
    try:
        data = json.load(open(PROMPTS_FILE, encoding="utf-8"))
        return data.get(key, {}).get("prompt") or default
    except Exception:
        return default


def llm_call(model: str, system: str, user: str, max_tokens: int = 2000) -> str:
    """
    يستدعي المزوّد المناسب حسب format الموديل:
    - anthropic/xxx → Anthropic API مباشرة
    - openai/xxx    → OpenAI API مباشرة
    - openrouter/xx → OpenRouter API مباشرة
    - claude/gpt/..  → LiteLLM proxy (aliases)
    """
    keys  = _read_api_keys()
    parts = model.split("/", 1)
    provider = parts[0].lower() if len(parts) > 1 else ""
    model_id = parts[1] if len(parts) > 1 else model

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]

    # ── Anthropic مباشرة ──────────────────────────────────────────────
    if provider == "anthropic":
        api_key = keys.get("ANTHROPIC_API_KEY","")
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "system": system,
                "messages": [{"role":"user","content":user}],
                "max_tokens": max_tokens,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    # ── OpenAI مباشرة ─────────────────────────────────────────────────
    if provider == "openai":
        api_key = keys.get("OPENAI_API_KEY","")
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model_id, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ── OpenRouter مباشرة ─────────────────────────────────────────────
    # الموديلات المجانية على OpenRouter (":free") كثيراً ما تُرفض بـ 429
    # rate-limit مؤقت — نعيد المحاولة مع انتظار قصير (احترام "Retry-After"
    # الموجود في رد الخطأ نفسه لو وُجد) بدل الفشل الفوري.
    if provider == "openrouter":
        api_key = keys.get("OPENROUTER_API_KEY","")
        last_exc = None
        for attempt in range(3):
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model_id, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3},
                timeout=120,
            )
            if resp.status_code == 429:
                wait_s = 8
                try:
                    wait_s = int(resp.json()["error"]["metadata"]["headers"]["Retry-After"])
                except Exception:
                    pass
                last_exc = Exception(f"rate-limited (429) — انتظار {wait_s}ث ثم إعادة المحاولة")
                time.sleep(min(wait_s, 15) + 1)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        raise last_exc or Exception("OpenRouter rate-limited بعد 3 محاولات")

    # ── LiteLLM proxy (aliases: claude, gpt, openrouter-auto) ──────────
    resp = requests.post(
        f"{LITELLM_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {LITELLM_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_pipeline(project: dict, status_cb=None) -> dict:
    """
    Pipeline تسلسلي — output كل agent يدخل context الـ agent التالي.
    """
    name        = project["name"]
    description = project["description"]
    requirements= project.get("requirements", description)
    repo        = project["repo_full_name"]
    doc_content = project.get("document_content", "")

    stages = {}
    context = f"Project: {name}\nDescription: {description}\nRequirements: {requirements}\n"

    # ── ١. محلل النصوص (لو في مستند) ─────────────────────────────────
    if doc_content:
        print("[1/6] محلل النصوص...")
        output = llm_call(
            model=_model("doc_analyzer"),
            system=_agent_prompt("doc_analyzer", "أنت محلل مستندات خبير. تستخرج البنية الهرمية من أي مستند بدقة تامة وتحولها لـ JSON."),
            user=f"{context}\nحلّل هذا المستند واستخرج بنيته الهرمية:\n\n{doc_content[:6000]}\n\nأخرج JSON يعكس الهيكل + كيف يترجم لمشروع برمجي.",
        )
        stages["doc_analyzer"] = output
        context += f"\n--- تحليل المستند ---\n{output}\n"

    # ── ٢. الباحث ──────────────────────────────────────────────────────
    if status_cb: status_cb("researcher")
    print("[2/6] الباحث...")
    output = llm_call(
        model=_model("researcher"),
        system=_agent_prompt("researcher", "أنت باحث تقني خبير. توصي بأفضل tech stack وتحدد التحديات المتوقعة."),
        user=f"{context}\nاقترح أنسب tech stack لهذا المشروع مع تبرير كل اختيار والتحديات المتوقعة.",
        max_tokens=1500,
    )
    stages["researcher"] = output
    context += f"\n--- نتيجة البحث ---\n{output}\n"

    # ── ٣. المصمم ──────────────────────────────────────────────────────
    if status_cb: status_cb("designer")
    print("[3/6] المصمم...")
    output = llm_call(
        model=_model("designer"),
        system=_agent_prompt("designer", "أنت مصمم UI/UX خبير. تصمم هيكل المشروع والشاشات والمكونات."),
        user=f"{context}\nصمّم الشاشات والمكونات وتدفق المستخدم لهذا المشروع.",
        max_tokens=1500,
    )
    stages["designer"] = output
    context += f"\n--- التصميم ---\n{output}\n"

    # ── ٤. المخطط التقني ────────────────────────────────────────────────
    if status_cb: status_cb("planner")
    print("[4/6] المخطط...")
    output = llm_call(
        model=_model("planner"),
        system=_agent_prompt("planner", "أنت مهندس برمجيات خبير. تكتب خططاً تقنية مفصّلة قابلة للتنفيذ مباشرة."),
        user=f"{context}\nاكتب خطة تقنية كاملة تشمل: هيكل الملفات، قائمة الـ dependencies، skeleton code لكل ملف، أوامر التشغيل، README.md. الخطة يجب أن تكون كاملة للتنفيذ المباشر.",
        max_tokens=3000,
    )
    stages["planner"] = output
    context += f"\n--- الخطة التقنية ---\n{output}\n"

    # ── ٥. حلّال المشاكل (مراجعة الخطة) ─────────────────────────────
    if status_cb: status_cb("problem_solver")
    print("[5/6] حلّال المشاكل...")
    output = llm_call(
        model=_model("problem_solver"),
        system=_agent_prompt("problem_solver", "أنت خبير debugging ومراجعة تقنية. تحدد المشاكل والتعارضات في الخطط وتصلحها."),
        user=f"{context}\nراجع الخطة التقنية وحدد أي مشاكل أو تعارضات أو نقاط ضعف، ثم أصدر خطة معدّلة ومحسّنة.",
        max_tokens=2000,
    )
    stages["problem_solver"] = output
    final_plan = output
    context += f"\n--- الخطة النهائية ---\n{output}\n"

    # ── ٦. المراجع ─────────────────────────────────────────────────────
    if status_cb: status_cb("reviewer")
    print("[6/6] المراجع...")
    output = llm_call(
        model=_model("reviewer"),
        system=_agent_prompt("reviewer", "أنت مراجع كود خبير. تتحقق من جودة الخطط وتضع معايير القبول."),
        user=f"{context}\nأعدّ تقرير جودة نهائي: هل الخطة تغطي المتطلبات؟ هل فيه مخاوف أمنية؟ ما معايير القبول؟ ما توصياتك للمبرمج؟",
        max_tokens=1500,
    )
    stages["reviewer"] = output

    return {
        "stages":       stages,
        "final_plan":   final_plan,
        "full_context": context,
    }
