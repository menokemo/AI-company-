"""
pipeline.py — Multi-agent pipeline بدون crewai.
كل agent = LLM call منفصل بـ context من الـ agent السابق.
"""
import os, json, requests

LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "")

def _model(env_key: str, default: str = "claude") -> str:
    return os.environ.get(env_key, default)

def llm_call(model: str, system: str, user: str, max_tokens: int = 2000) -> str:
    """استدعاء LiteLLM مباشرة."""
    resp = requests.post(
        f"{LITELLM_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {LITELLM_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_pipeline(project: dict) -> dict:
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
            model=_model("AGENT_DOC_ANALYZER_MODEL"),
            system="أنت محلل مستندات خبير. تستخرج البنية الهرمية من أي مستند بدقة تامة وتحولها لـ JSON.",
            user=f"{context}\nحلّل هذا المستند واستخرج بنيته الهرمية:\n\n{doc_content[:6000]}\n\nأخرج JSON يعكس الهيكل + كيف يترجم لمشروع برمجي.",
        )
        stages["doc_analyzer"] = output
        context += f"\n--- تحليل المستند ---\n{output}\n"

    # ── ٢. الباحث ──────────────────────────────────────────────────────
    print("[2/6] الباحث...")
    output = llm_call(
        model=_model("AGENT_RESEARCHER_MODEL"),
        system="أنت باحث تقني خبير. توصي بأفضل tech stack وتحدد التحديات المتوقعة.",
        user=f"{context}\nاقترح أنسب tech stack لهذا المشروع مع تبرير كل اختيار والتحديات المتوقعة.",
        max_tokens=1500,
    )
    stages["researcher"] = output
    context += f"\n--- نتيجة البحث ---\n{output}\n"

    # ── ٣. المصمم ──────────────────────────────────────────────────────
    print("[3/6] المصمم...")
    output = llm_call(
        model=_model("AGENT_DESIGNER_MODEL"),
        system="أنت مصمم UI/UX خبير. تصمم هيكل المشروع والشاشات والمكونات.",
        user=f"{context}\nصمّم الشاشات والمكونات وتدفق المستخدم لهذا المشروع.",
        max_tokens=1500,
    )
    stages["designer"] = output
    context += f"\n--- التصميم ---\n{output}\n"

    # ── ٤. المخطط التقني ────────────────────────────────────────────────
    print("[4/6] المخطط...")
    output = llm_call(
        model=_model("AGENT_PLANNER_MODEL"),
        system="أنت مهندس برمجيات خبير. تكتب خططاً تقنية مفصّلة قابلة للتنفيذ مباشرة.",
        user=f"{context}\nاكتب خطة تقنية كاملة تشمل: هيكل الملفات، قائمة الـ dependencies، skeleton code لكل ملف، أوامر التشغيل، README.md. الخطة يجب أن تكون كاملة للتنفيذ المباشر.",
        max_tokens=3000,
    )
    stages["planner"] = output
    context += f"\n--- الخطة التقنية ---\n{output}\n"

    # ── ٥. حلّال المشاكل (مراجعة الخطة) ─────────────────────────────
    print("[5/6] حلّال المشاكل...")
    output = llm_call(
        model=_model("AGENT_SOLVER_MODEL"),
        system="أنت خبير debugging ومراجعة تقنية. تحدد المشاكل والتعارضات في الخطط وتصلحها.",
        user=f"{context}\nراجع الخطة التقنية وحدد أي مشاكل أو تعارضات أو نقاط ضعف، ثم أصدر خطة معدّلة ومحسّنة.",
        max_tokens=2000,
    )
    stages["problem_solver"] = output
    final_plan = output
    context += f"\n--- الخطة النهائية ---\n{output}\n"

    # ── ٦. المراجع ─────────────────────────────────────────────────────
    print("[6/6] المراجع...")
    output = llm_call(
        model=_model("AGENT_REVIEWER_MODEL"),
        system="أنت مراجع كود خبير. تتحقق من جودة الخطط وتضع معايير القبول.",
        user=f"{context}\nأعدّ تقرير جودة نهائي: هل الخطة تغطي المتطلبات؟ هل فيه مخاوف أمنية؟ ما معايير القبول؟ ما توصياتك للمبرمج؟",
        max_tokens=1500,
    )
    stages["reviewer"] = output

    return {
        "stages":       stages,
        "final_plan":   final_plan,
        "full_context": context,
    }
