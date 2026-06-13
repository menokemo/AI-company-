"""
مهام CrewAI — كل مهمة تأخذ output السابقة كـ context.
Pipeline تسلسلي: لا تعارض، كل موظف ينتظر السابق.
"""
from crewai import Task


def make_tasks(agents: dict, project: dict) -> list:
    """
    project = {
        name, description, requirements, repo_full_name,
        document_content (اختياري — محتوى الملف المرفوع)
    }
    """
    name        = project["name"]
    description = project["description"]
    requirements= project.get("requirements", description)
    repo        = project["repo_full_name"]
    doc_content = project.get("document_content", "")

    tasks = []

    # ── ١. محلل النصوص (فقط إذا في مستند) ──────────────────────────────
    if doc_content:
        t1 = Task(
            description=f"""حلّل المستند التالي واستخرج بنيته الهرمية الكاملة:

{doc_content[:8000]}

المطلوب:
1. استخرج الهيكل الهرمي (أبواب → فصول → أقسام → أفرع)
2. حوّله لـ JSON واضح
3. اقترح كيف يُترجم هذا الهيكل لمشروع برمجي ({name})
4. وضّح أي عناصر تفاعلية ستحتاجها كل وحدة""",
            expected_output="JSON يعكس الهيكل الهرمي + خريطة ترجمته لمشروع برمجي",
            agent=agents["doc_analyzer"],
        )
        tasks.append(t1)

    # ── ٢. الباحث ───────────────────────────────────────────────────────
    context_prev = [tasks[-1]] if tasks else []
    t2 = Task(
        description=f"""ابحث عن أفضل الممارسات لمشروع: "{name}"

الوصف: {description}
المتطلبات: {requirements}
{'البنية المستخرجة من المستند: (راجع المهمة السابقة)' if doc_content else ''}

المطلوب:
1. أنسب tech stack (لغة، framework، قاعدة بيانات)
2. أبرز مشاريع مشابهة وما يميّزها
3. أهم التحديات المتوقعة وكيف تتجنبها
4. توصيات الأمان والأداء""",
        expected_output="تقرير بحثي: tech stack + تحديات + توصيات",
        agent=agents["researcher"],
        context=context_prev,
    )
    tasks.append(t2)

    # ── ٣. المصمم ───────────────────────────────────────────────────────
    t3 = Task(
        description=f"""صمّم هيكل مشروع "{name}" بناءً على البحث السابق.

المطلوب:
1. قائمة الشاشات/الصفحات مع وصف كل واحدة
2. المكونات الرئيسية وعلاقاتها
3. تدفق المستخدم (user flow) من البداية للنهاية
4. هيكل البيانات الأساسي
5. الألوان والنمط البصري المقترح""",
        expected_output="تصميم كامل: شاشات + مكونات + user flow + بيانات",
        agent=agents["designer"],
        context=[t2],
    )
    tasks.append(t3)

    # ── ٤. المخطط التقني ─────────────────────────────────────────────────
    t4 = Task(
        description=f"""حوّل التصميم السابق لخطة تقنية قابلة للتنفيذ المباشر لمشروع "{name}".

الريبو: {repo}

المطلوب (بالتفصيل الكامل):
1. هيكل الملفات والمجلدات الكامل
2. قائمة الـ dependencies مع الإصدارات
3. كود كل ملف رئيسي (skeleton)
4. الـ APIs والـ endpoints إن وجدت
5. أوامر التشغيل والـ build
6. ملف README.md

الخطة يجب أن تكون جاهزة للتنفيذ المباشر دون أسئلة إضافية.""",
        expected_output="خطة تقنية كاملة: ملفات + كود + dependencies + README",
        agent=agents["planner"],
        context=[t3],
    )
    tasks.append(t4)

    # ── ٥. مراجعة الخطة (حلّال المشاكل يراجع قبل التنفيذ) ──────────────
    t5 = Task(
        description=f"""راجع الخطة التقنية السابقة لمشروع "{name}" وحدّد:

1. أي تعارضات أو مشاكل في الخطة
2. نقاط الضعف المحتملة
3. اقتراحات لتحسين الخطة قبل التنفيذ
4. تأكيد أن الخطة قابلة للتنفيذ

أصدر خطة معدّلة ومحسّنة إذا لزم الأمر.""",
        expected_output="تقرير مراجعة + خطة معدّلة جاهزة للتنفيذ",
        agent=agents["problem_solver"],
        context=[t4],
    )
    tasks.append(t5)

    # ── ٦. مراجعة نهائية للجودة ──────────────────────────────────────────
    t6 = Task(
        description=f"""بعد اكتمال خطة مشروع "{name}"، أعدّ تقرير جودة نهائي:

1. هل الخطة تغطي جميع المتطلبات؟
2. هل الكود المخطط يتبع best practices؟
3. هل فيه مخاوف أمنية؟
4. توصيات للمبرمج (OpenHands) أثناء التنفيذ
5. معايير قبول المشروع (acceptance criteria)

هذا التقرير سيُرسَل مع الخطة لـ OpenHands.""",
        expected_output="تقرير جودة + توصيات للمبرمج + معايير القبول",
        agent=agents["reviewer"],
        context=[t5],
    )
    tasks.append(t6)

    return tasks
