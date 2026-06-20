# AI Company — Project Summary

## الوصف
منظومة شركة برمجة بالذكاء الاصطناعي — تحوّل أفكار العملاء لتطبيقات حقيقية بشكل شبه أوتوماتيك.

## البنية التحتية

| الخدمة | البورت | الوظيفة |
|--------|--------|---------|
| Dashboard | 80 | لوحة التحكم الرئيسية (Sidebar + Tabs) |
| Open WebUI | 8888 | واجهة الدردشة + مدير المشروع |
| OpenHands | 3000 | AI Coding Agent |
| Infisical | 8080 | إدارة الـ secrets |
| LiteLLM | 4000 | Proxy للـ LLM APIs |
| Crew Pipeline | 9002 | Pipeline الـ 6 agents |
| Tools API | 9000 | API داخلي |
| Portainer | 9443 | إدارة Docker |

## Dashboard المحدثة (v1.7.0)

### المزايا الجديدة
- **Sidebar Navigation** - تصميم حديث مع 5 tabs رئيسية
- **Responsive Design** - يعمل بكمال على Desktop و Mobile و Tablet
- **Hamburger Menu** - قائمة محمول بسيطة وسهلة الاستخدام
- **Tab Switching** - تنقل سلس بين الأقسام المختلفة
- **State Persistence** - تذكر آخر tab استخدمته عن طريق localStorage

### الـ Tabs الرئيسية
1. **🚀 Getting Started** - خطوات البدء والـ setup instructions
2. **📡 Services** - حالة الخدمات (health checks) + credentials + prompts
3. **🤖 Models** - إدارة موديلات الـ agents
4. **📊 History** - سجل تنفيذات الـ crew pipeline
5. **🔑 Infisical** - معالج إعداد Infisical ومزامنة الـ secrets

### الـ Responsive Breakpoints
- **Desktop** (> 768px): Sidebar ثابت على اليسار (240px)
- **Tablet/Mobile** (≤ 768px): Hamburger menu مع sidebar قابل للإغلاق
- **Small Mobile** (≤ 480px): تقليل padding والـ font sizes

## التثبيت

```bash
TOKEN="ghp_xxx"
curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github.raw+json" \
  "https://raw.githubusercontent.com/menokemo/AI-company-/main/install.sh" \
  -o /tmp/install.sh && \
sudo bash /tmp/install.sh --github-token "$TOKEN"
```

## Flow المشروع

```
Client → Open WebUI (مدير المشروع)
    ↓
Crew Pipeline (6 agents):
  1. Document Analyzer
  2. Researcher
  3. Designer (mockups)
  4. Planner
  5. Problem Solver
  6. Code Reviewer
    ↓
OpenHands → GitHub Repo → Pull Request
```

## الـ Credentials
كلها في: Dashboard → Services tab → Access Credentials

## الـ Post-Install Steps
1. Infisical → Sign Up → Machine Identity
2. Dashboard → Infisical tab → Setup Wizard
3. Infisical → أضف: ANTHROPIC_API_KEY, GITHUB_TOKEN, GIT_USERNAME
4. Dashboard → Sync Now
5. Dashboard → Models tab → اختار موديل لكل agent → Save

## الملفات المهمة

| الملف | الوظيفة |
|-------|---------|
| `install.sh` | التثبيت الكامل |
| `infrastructure/docker-compose.yml` | تعريف الخدمات |
| `infrastructure/.env` | كل الـ secrets (مولّدة) |
| `config/models.json` | موديلات الـ agents |
| `config/agent-prompts.json` | prompts الـ agents |
| `config/run_history.json` | سجل أعمال الموظفين (يُكتب أوتوماتيك) |
| `tools-api/system-prompt.md` | prompt مدير المشروع |
| `crew-service/pipeline.py` | Pipeline الـ 6 agents |
| `start-page/index.html` | Dashboard (الجديدة مع Sidebar) |
| `secrets-sync/setup-*.py` | إعداد الخدمات |

## الميزات
- **سجل أعمال الموظفين** (History tab في Dashboard): يعرض كل تشغيلة سابقة — ماذا أنتج كل agent + نتيجة OpenHands، محفوظ على القرص
- **إعادة محاولة تلقائية**: لـ race condition معروف في OpenHands SDK (sandbox startup)، ولـ rate-limit الموديلات المجانية في OpenRouter
- **Dashboard Responsive**: يعمل على جميع الأجهزة بدون مشاكل

## الميزات (تتمة)
- **التحقق من حالة المشروع**: مدير المشروع كان يقول "لا أستطيع التحقق" عند سؤاله "هل خلص؟" لأنه ليس له ذاكرة لتقدّم OpenHands. أداة جديدة `check_project_status` تتحقق من GitHub مباشرة (كومتات + Pull Requests) وترجع حالة حقيقية. الـ API: `POST /project-status` (tools-api).

## جُرِّب وتم التراجع عنه
- **عرض توقيت جنب اسم المرسل (زي واتساب)**: المطلوب الحقيقي كان عنصر UI منفصل (وقت ظاهر جنب اسم المرسل في الواجهة)، لا نص داخل الرسالة. جُرِّب حقن التوقيت داخل محتوى الرسالة نفسها عبر Open WebUI Filter (`inlet`/`outlet`) — رُفض لأنه يلوّث نص المحادثة الفعلي. **الاستنتاج:** هذه خاصية عرض في الواجهة الأمامية لـ Open WebUI نفسه (Frontend)، خارج نطاق تحكّم الـ Tools/Filters التي نبنيها — يتطلب تعديل الكود المصدري لـ Open WebUI مباشرة (fork)، خارج نطاق المشروع الحالي.

## مُخطَّط له (لم يُنفَّذ بعد)
- **إعادة تصميم لوحة التحكم**: تحويلها من صفحة واحدة طويلة لـ sidebar + تبويبات (نظرة عامة، إعداد Infisical، الموديلات، سجل الأعمال، بيانات الدخول)، مع دعم كامل للموبايل (responsive). الخطة المتفق عليها: 4 مراحل — (١) تخطيط التبويبات [تم الاتفاق]، (٢) بناء الهيكل على الديسكتوب، (٣) دعم الموبايل، (٤) تلميع نهائي. **لم نبدأ التنفيذ بعد.**

## الـ PENDING
- [ ] PR creation من OpenHands
- [ ] تحسينات إضافية على الـ Dashboard (themes, dark mode)
