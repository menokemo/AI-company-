"""
تعريف موظفي CrewAI — كل موظف بموديل مستقل قابل للتغيير من Infisical.
"""
import os
from crewai import Agent
from litellm import completion

LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "")

def _model(env_key: str, default: str) -> str:
    """يقرأ الموديل من env — سهل التغيير من Infisical."""
    return f"openai/{os.environ.get(env_key, default)}"


def make_agents() -> dict:
    base = {
        "api_base": LITELLM_URL,
        "api_key":  LITELLM_KEY,
        "verbose":  False,
        "allow_delegation": False,
    }

    doc_analyzer = Agent(
        role="محلل النصوص والمستندات",
        goal="استخراج البنية الهرمية الكاملة من أي مستند (كتاب، PDF، ملف نصي) بدقة تامة.",
        backstory="""خبير في تحليل المستندات وفهم بنيتها. يستطيع تحويل أي ملف 
        لهيكل JSON واضح يعكس التسلسل الهرمي: أبواب، فصول، أقسام، أفرع.""",
        llm=_model("AGENT_DOC_ANALYZER_MODEL", "claude"),
        **base,
    )

    researcher = Agent(
        role="باحث تقني",
        goal="البحث عن أفضل الممارسات والتقنيات المناسبة للمشروع.",
        backstory="""خبير في تقييم التقنيات واختيار الـ tech stack الأنسب. 
        يحلل متطلبات المشروع ويوصي بالأدوات والأطر المثالية.""",
        llm=_model("AGENT_RESEARCHER_MODEL", "claude"),
        **base,
    )

    designer = Agent(
        role="مصمم المشروع",
        goal="تصميم هيكل المشروع وواجهة المستخدم بناءً على المتطلبات.",
        backstory="""مصمم متمرس يحوّل المتطلبات لهيكل واضح: مكونات، شاشات، 
        تدفق المستخدم. مخرجاته تصبح المدخل المباشر للمخطط التقني.""",
        llm=_model("AGENT_DESIGNER_MODEL", "claude"),
        **base,
    )

    planner = Agent(
        role="مخطط تقني",
        goal="تحويل التصميم لخطة تقنية مفصّلة قابلة للتنفيذ مباشرة.",
        backstory="""مهندس برمجيات يكتب خططاً تقنية شاملة: هيكل الملفات، 
        الـ APIs، قواعد البيانات، والتبعيات. خطته تُنفَّذ مباشرة بدون أسئلة.""",
        llm=_model("AGENT_PLANNER_MODEL", "gpt"),
        **base,
    )

    problem_solver = Agent(
        role="حلّال المشاكل التقنية",
        goal="تحليل الأخطاء البرمجية وإيجاد حلول دقيقة وعملية.",
        backstory="""خبير debugging لديه القدرة على تحليل stack traces والأخطاء 
        وإيجاد الحل الصحيح من أول مرة. لا يقترح حلولاً جزئية.""",
        llm=_model("AGENT_SOLVER_MODEL", "claude"),
        **base,
    )

    reviewer = Agent(
        role="مراجع الكود",
        goal="مراجعة الكود للتأكد من الجودة والأمان والأداء.",
        backstory="""مراجع كود صارم يفحص: جودة الكود، الأمان، الأداء، 
        وامتثاله للمعايير. يعطي تقريراً واضحاً بالمشاكل والتحسينات المطلوبة.""",
        llm=_model("AGENT_REVIEWER_MODEL", "openrouter-auto"),
        **base,
    )

    return {
        "doc_analyzer":   doc_analyzer,
        "researcher":     researcher,
        "designer":       designer,
        "planner":        planner,
        "problem_solver": problem_solver,
        "reviewer":       reviewer,
    }
