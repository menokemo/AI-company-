# المشاكل وحلولها — BUGS_AND_FIXES

> كل مشكلة نقابلها أثناء التطوير تُوثَّق هنا مع حلّها، عشان ما تتكررش، وعشان أي حد جديد يستفيد.

## الصيغة

لكل مشكلة:

- **العنوان:** وصف مختصر.
- **التاريخ:** تاريخ ظهور المشكلة.
- **الوصف:** المشكلة بالتفصيل.
- **السبب:** السبب الجذري.
- **الحل المطبّق:** الحل النهائي الذي نجح.
- **ملاحظات:** أي حلول جُرّبت وفشلت (ولماذا) لتجنّبها مستقبلًا.

> قاعدة: أي حل يُجرَّب ولا يحلّ المشكلة، يُزال فورًا قبل تجربة حل آخر، للحفاظ على نظافة الكود.














---

## جلسة 2026-06-17 (تابع) — "اخترت التصميم… بس مافيش حاجة وصلت لـ OpenHands"

المستخدم اختار تصميم، مدير المشروع أنشأ الريبو فعليًا، لكن OpenHands لم يبدأ أي عمل ملحوظ.

### السبب
هذا [bug معروف في OpenHands نفسه](https://github.com/OpenHands/OpenHands/issues/12500) — race condition وقت إقلاع الـ sandbox container. الـ orchestrator بيفحص جاهزية الـ sandbox بسرعة كبيرة، فلو احتاج الـ sandbox ثوانٍ قليلة زيادة (شائع لو الجهاز تحت ضغط)، يُعلَن "Sandbox entered error state" رغم إن الـ container نفسه يقلع بنجاح تام بعد ثوانٍ قليلة (تأكدنا بفحص توقيت start-task: تم تسجيل ERROR في `19:21:04`، بينما السيرفر فعليًا اكتمل إقلاعه في `19:21:08` — أي بعد الخطأ بـ ٤ ثوانٍ فقط).

### الإصلاح
`tools-api/server.py`: `start_coding()` يفحص حالة المحادثة بعد إنشائها مباشرة، ولو ظهرت `ERROR`، يعيد المحاولة بمحادثة جديدة تلقائيًا (حتى ٣ محاولات كاملة) قبل الإفادة بالفشل.

### الدرس المستفاد
بعض الأخطاء مصدرها الأداة الخارجية نفسها (OpenHands) لا كودنا — في هذه الحالة لا يوجد "إصلاح جذري" حقيقي ممكن من جانبنا (المشكلة موجودة في OpenHands SDK)، فالحل العملي هو إعادة محاولة تلقائية ذكية بدل ترك المستخدم بدون أي كود.

---
---

## جلسة 2026-06-17 (تابع) — OpenHands يطلب إعداد يدوي بعد كل تثبيت نظيف

بعد تثبيت نظيف من الصفر، فتح المستخدم OpenHands فظهر له popup "AI Provider Configuration" يطلب إدخال API key يدويًا.

### السبب
إعدادات LLM الخاصة بـ OpenHands V1 (api_key, base_url) تُخزَّن في قاعدة بيانات OpenHands نفسها عبر `/api/v1/settings` (`agent_settings_diff`) — اكتشفنا هذا في جلسة سابقة وضبطناه **يدويًا عبر curl** وقت التشخيص، لكن لم نُضِف هذه الخطوة أبداً لأي سكربت تلقائي. أي تثبيت جديد أو مسح كامل يفقد هذا الإعداد تمامًا، فيظهر طلب الإعداد اليدوي من جديد.

### إصلاح إضافي اكتُشف بالتزامن
خطوة "ربط GitHub بـ OpenHands" في `infisical-sync.sh` كانت تستخدم `http://localhost:3000` **بدون شرط** — يعمل فقط لو السكربت شغّال على الـ host مباشرة (كما يحدث أول مرة في `install.sh`)، لكنه يفشل بصمت لو نُفّذ من داخل `tools-api` (عبر زر "Sync Now" من لوحة التحكم)، لأن `localhost` داخل الـ container يشاور على نفسه لا على `ai-openhands`.

### الإصلاح
أُضيفت لـ `infisical-sync.sh`:
1. اكتشاف العنوان الصحيح لـ OpenHands ديناميكيًا (`ai-openhands:3000` داخل container، `localhost:3000` على الـ host) — يُستخدم في **كل** الاستدعاءات لـ OpenHands بما فيها ربط GitHub
2. خطوة جديدة تلقائية تضبط `agent_settings_diff.llm.{api_key, base_url}` عبر `/api/v1/settings` في كل مرة يُشغَّل الـ sync — فلا حاجة لأي إعداد يدوي بعد كل تثبيت/مسح جديد

---
---

## جلسة 2026-06-17 (تابع) — تثبيت نظيف من الصفر: الموديلات لا تظهر بعد Sync

بعد مسح الـ VM بالكامل وتثبيت نظيف، المستخدم أضاف المفاتيح في Infisical وعمل "Sync Now" بنجاح — لكن قائمة الموديلات في لوحة التحكم ظلّت فاضية.

### السبب الجذري
`tools-api/server.py`: المتغيرات الحساسة (`GITHUB_TOKEN`, وفحص مفاتيح المزوّدين في `/config/providers`) كانت تُقرأ من `os.environ` — قيمة **مجمّدة وقت بدء تشغيل الـ container فقط**. السكربت `infisical-sync.sh` يكتب القيم الجديدة في ملف `.env` على القرص، لكنه **لا** يعيد تشغيل `tools-api` نفسه عمداً (لأن الـ sync يُستدعى من داخل `tools-api` نفسه عبر `/system/sync` — إعادة تشغيله سيقطع الرد قبل أن يكتمل). النتيجة: أي مفتاح جديد يُضاف بعد أول تشغيل **لا يظهر مطلقاً** في `/config/providers` ولا يُستخدم في عمليات GitHub الفعلية، حتى تتم إعادة تشغيل الـ container يدويًا بالكامل.

### الإصلاح
- `get_available_providers()`: تقرأ الآن ملف `.env` مباشرة من القرص في كل استدعاء (بدل `os.environ` المجمّدة)
- `GITHUB_TOKEN`: تحوّل من `constant` ثابت وقت الاستيراد إلى دالة `get_github_token()` تُقرأ في كل استدعاء فعلي
- نفس الإصلاح الدفاعي طُبّق في `crew-service/crew.py` لـ `create_pr()`

### الدرس المستفاد
أي قيمة بتُحدَّث عبر "Sync"، ولا تملك الخدمة قدرة على إعادة تشغيل نفسها بأمان، يجب أن تُقرأ من الملف على القرص **في وقت الاستخدام الفعلي** — لا أن تُخزَّن كـ constant وقت الاستيراد.

---
---

## جلسة 2026-06-17 (تابع) — Audit شامل: hardcoded values كانت بتلغي اختيارات لوحة التحكم

المستخدم لاحظ إن كل المنظومة بتشتغل بـ Claude بس، رغم اختيار موديلات مختلفة من لوحة التحكم. تم عمل audit كامل للريبو فلقينا 5 مشاكل حقيقية:

### 🔴 [الأهم] `pipeline.py`: `_model()` كانت بتقرأ env var غير موجود
```python
# قبل (خطأ):
def _model(env_key, default="claude"):
    return os.environ.get(env_key, default)   # env_key="doc_analyzer" — مفيش متغيّر بهذا الاسم!

# بعد (صحيح):
def _model(agent_key, default="claude"):
    cfg = json.load(open(CONFIG_FILE))
    return cfg.get(agent_key) or default
```
**الأثر:** كل الـ 6 agents في crew pipeline (محلل النصوص، الباحث، المصمم، المخطط، حلّال المشاكل، المراجع) كانوا **دايماً** بيستخدموا alias `"claude"` بغض النظر عن أي اختيار محفوظ في `models.json` من لوحة التحكم. هذا كان موجوداً منذ كتابة الكود الأصلي — مش حاجة استجدت من تعديلاتنا.

### 🔴 `crew.py`: `start_openhands()` فيها `"llm_model": "openai/claude"` مكتوبة يدويًا
نفس النمط بالظبط اللي صلحناه في `tools-api/server.py`، لكن في مسار تنفيذ منفصل بالكامل (الـ `/run-pipeline` الكامل، مختلف عن `/create-and-start`). تم إصلاحها بدالة `get_coder_model()` تقرأ `models.json["coder"]`.

### 🟡 IP شخصي (`192.168.2.29`) كـ fallback في حالة غياب `HOST_IP`
موجود في `tools-api/server.py` و `tools-api/openwebui_tools.py`. خطر لأي تنصيب على VM مختلف. تم تغييره لـ `"localhost"`.

### 🟡 `setup-infisical.py`: `BASE` مكتوبة `http://localhost:8080` بدون إمكانية تغييرها
نفس فئة الـ bug اللي صلحناه سابقاً لـ Open WebUI (لما السكربت يتنفّذ من داخل container، `localhost` تشاور على نفسه). أصبحت قابلة للتعديل عبر `INFISICAL_API_URL`.

### 🟡 `crew-service/ui.html`: قائمة موديلات فيها قيم غير موجودة فعليًا
`MODELS = [...,"claude-opus","gpt-4o"]` — لكن `litellm-config.yaml` يعرّف فقط 3 aliases (`claude`, `gpt`, `openrouter-auto`). اختيار أي من القيمتين الزائدتين من واجهة crew-service مباشرة كان سيفشل. تم حذفهما.

### 🧹 كود ميت تم حذفه
- `code-writer/` — تصميم قديم (v0.23.0) استُبدل بـ OpenHands بعد كده، غير متصل بـ `docker-compose.yml` أبداً
- `llm-gateway/` — نسخة مكررة قديمة من `infrastructure/litellm-config.yaml`، غير مستخدمة

### الدرس المستفاد
أي قيمة (موديل، IP، URL) لازم تُقرأ من `config/models.json` أو متغيّرات البيئة **فعليًا وقت التنفيذ** — لا اعتماد على افتراضات مكتوبة في الكود، حتى لو بدت "افتراض منطقي وقتها".

---
---

## جلسة 2026-06-17 (تابع) — Sync لا يُطبّق الـ secrets فعلياً

### BUG: `docker restart` لا يُعيد قراءة `env_file`
- **المشكلة:** `infisical-sync.sh` كان يستخدم `docker restart ai-litellm` بعد تحديث `.env` — لكن `docker restart` يعيد تشغيل الـ container بنفس الـ environment القديم وقت الإنشاء، ولا يُعيد قراءة `env_file` من docker-compose
- **الأثر:** الـ API keys الجديدة من Infisical تُكتب في `.env` بنجاح، لكن LiteLLM يستمر بدونها → `litellm.BadRequestError: You didn't provide an API key`
- **الحل:** استخدام `docker compose up -d --force-recreate <service>` بدل `docker restart`

### BUG: `docker-compose.yml` نفسه غير mounted في tools-api container
- **المشكلة:** الـ `--force-recreate` يحتاج `docker compose` يقرأ ملف الـ compose، لكنه غير موجود جوه الـ container
- **الحل:** mount صريح: `docker-compose.yml:/opt/ai-company/infrastructure/docker-compose.yml:ro`

### BUG: `base_model_id` لمدير المشروع غير معروف لـ Open WebUI
- **المشكلة:** `models.json` يخزّن `"manager": "openai/gpt-4o"` (provider/model خام) — لكن Open WebUI يعرف فقط الـ aliases المعرّفة في `litellm-config.yaml` (`claude`, `gpt`, `openrouter-auto`)، فيظهر **"Model not found"**
- **الحل:** mapping صريح في `setup-openwebui.py`: `{"anthropic":"claude", "openai":"gpt", "openrouter":"openrouter-auto"}`

### النتيجة
```
[+] إعادة تشغيل الخدمات بالمفاتيح الجديدة...
[+] ✅ تم الـ sync بنجاح!
```
الـ API keys دلوقتي تُحقن فعلياً في LiteLLM container بعد كل sync، ومدير المشروع يتعرّف على الموديل الصحيح.

---
---

## جلسة 2026-06-17 — Project Manager Creation: السبب الجذري الكامل

سلسلة من 9 bugs متراكمة كانت بتمنع إنشاء موديل "مدير المشروع" في Open WebUI من داخل tools-api container:

### 1. BASE URL hardcoded
`BASE = "http://localhost:8888"` — من داخل tools-api container، `localhost` يشاور على نفسه مش Open WebUI.
**الحل:** `os.environ.get("OPENWEBUI_URL", "http://localhost:8888")`

### 2. Internal port غلط
docker-compose port mapping `8888:8080` يعني الـ port الداخلي هو 8080 لا 8888.
**الحل:** `OPENWEBUI_URL=http://ai-open-webui:8080` في docker-compose.

### 3. tools-api/ directory غير mounted
`system-prompt.md` و `openwebui_tools.py` غير موجودين جوه الـ container (فقط server.py بيتم COPY في build).
**الحل:** mount صريح لكل ملف على نفس المسار المطلق في docker-compose.

### 4. منطق "tool exists" كان بيقفل الكود كله
`if existing: return 0` كان بيوقف قبل الوصول لقسم إنشاء الموديل بالكامل.
**الحل:** فصل منطق رفع الـ tool عن منطق إنشاء الموديل.

### 5. Model id فيه hyphens
`ai-company-project-manager` — Open WebUI يرفض الـ hyphens في الـ id.
**الحل:** `ai_company_project_manager`.

### 6. Key mismatch بين الكود والـ config
الكود بيدوّر على `project_manager` لكن `models.json` بيستخدم `manager`.
**الحل:** توحيد الاسم لـ `manager` في كل الملفات.

### 7. Hardcoded config path
`/opt/ai-company/config/models.json` غير موجود جوه الـ container (الـ volume على `/app/config`).
**الحل:** `os.environ.get("CONFIG_FILE", "/app/config/models.json")`.

### 8. Trailing slash في `/api/v1/models/`
بيرجع الـ SPA HTML (200 OK) مش JSON. بدون الـ slash بيرجع الـ API الصحيح.
**الحل:** شيل الـ trailing slash + قراءة `.get("data", [])` من الرد.

### 9. `access_grants: null` بيكسر pydantic validation
Open WebUI's `ModelForm` schema يطلب `access_grants` كـ list مش None — كان بيرجع 500 Internal Server Error.
**الحل:** إضافة `"access_grants": []` و `"is_active": True` في الـ payload.

### النتيجة النهائية
```
[✓] Tool already exists — skipping upload
[✓] Project Manager model updated!
```
ظهر فعلياً في Open WebUI ✅

---
---

## جلسة 2026-06-16 (مساء) — Wizard + UX Fixes

### FEATURE: Infisical Setup Wizard
- **المشكلة:** المستخدم لا يعرف الفرق بين Identity ID والـ Universal Auth Client ID
- **الحل:** Wizard تفاعلي بـ 6 خطوات مع تحذيرات واضحة

### BUG: Wizard HTML لم يُضاف للمكان الصح
- **المشكلة:** الـ old_section string في Python لم يطابق الـ HTML الفعلي (فرق في التعليقات)
- **الحل:** مطابقة النص الحرفي الموجود في الملف

### BUG: JS يعرض "undefined" بدل الـ sync error
- **المشكلة:** `d2.error` غير موجود — الـ server يرجع `output` لا `error`
- **الحل:** `d2.error || d2.output.slice(-150) || "unknown"`

---
---

## جلسة 2026-06-16 (ليل) — Docker CLI + ENV_FILE + Sync Final Fix

### BUG: `docker` command not found داخل tools-api container
- **المشكلة:** infisical-sync.sh يحاول يعمل `docker compose restart` لكن docker CLI مش موجود في Alpine
- **الحل:** `apk add --no-cache docker-cli` في الـ Dockerfile

### BUG: `ENV_FILE` NameError في server.py
- **المشكلة:** push متأخر مسح التعريف `ENV_FILE = os.environ.get("ENV_FILE_PATH", ...)`
- **الحل:** إعادة إضافة التعريف في ثوابت الملف

### BUG: HOST_IP hardcoded default
- **المشكلة:** `HOST_IP = os.environ.get("HOST_IP", "192.168.2.29")` — default hardcoded
- **الحل:** تغيير default لـ `"localhost"`

### RESULT: Sync يشتغل الآن
- يتصل بـ Infisical ✅
- يسحب الـ API keys ✅  
- يحدّث .env ✅
- يعيد تشغيل الخدمات ✅

---
---

## جلسة 2026-06-16 (مساء) — Sync Button + tools-api Fixes

### BUG: `/system/sync` و `/system/configure` في `do_GET` بدل `do_POST`
- **المشكلة:** الـ endpoints دي في الـ GET handler فبترجع 404 لما الـ dashboard يبعت POST
- **الحل:** نقلهم لـ `do_POST` handler

### BUG: `/system/configure` مش بيحفظ الـ .env على disk
- **المشكلة:** كود بيعدّل `content` في الذاكرة بس ناقص `open(env_file,"w").write(content)`
- **الحل:** إضافة الكتابة على disk

### BUG: tools-api container مش فيه access للـ .env
- **المشكلة:** الـ .env موجود على الـ host بس مش مـ mounted في container
- **الحل:** إضافة volume mount في docker-compose: `infrastructure/.env:/opt/ai-company/infrastructure/.env`

### BUG: tools-api (Alpine) مش فيه bash أو curl
- **المشكلة:** `subprocess.run(["/bin/bash", ...])` يفشل لأن bash غير موجود في Alpine
- **الحل:** إضافة `RUN apk add --no-cache bash curl` في الـ Dockerfile

### BUG: `${BASH_SOURCE[0]}` مش شغّال في Alpine bash
- **المشكلة:** Alpine's bash لا يدعم `${BASH_SOURCE[0]}`
- **الحل:** استبدال بـ `$0`

### BUG: `infisical-sync.sh` يستخدم `localhost:8080` داخل الـ container
- **المشكلة:** من داخل tools-api container، Infisical مش على localhost
- **الحل:** إضافة `INFISICAL_API_URL=http://ai-infisical:8080` في docker-compose للـ tools-api

### BUG: Open WebUI tool id يحتوي على hyphens
- **المشكلة:** `ai-company-tools` → 400 error (only alphanumeric + underscores)
- **الحل:** `ai_company_tools`

### BUG: secrets-sync/ غير مـ mounted في tools-api container
- **المشكلة:** الـ sync script غير موجود داخل الـ container
- **الحل:** إضافة volume: `secrets-sync:/opt/ai-company/secrets-sync:ro`

---
---

## جلسة 2026-06-16 — Install Script Timing + Background Setup

### BUG: `docker compose wait` يبلوك للأبد
- **المشكلة:** `docker compose wait infisical` ينتظر الـ container يـ EXIT مش يبقى healthy — يبلوك للأبد
- **الحل:** استخدام `docker inspect` + `curl` للتحقق من الـ health

### BUG: Infisical يحتاج أكثر من 10 دقائق على أول تثبيت
- **المشكلة:** Infisical يحتاج 10-15 دقيقة لأول تشغيل (DB migrations + KMS init)
- **الحل:** نقل كل الـ setup لـ background script بعد التثبيت

### BUG: `curl` غير متاح داخل Infisical container
- **المشكلة:** healthcheck يستخدم `curl -sf` لكنه غير موجود في الـ container
- **الحل:** استخدام `wget` في healthcheck + curl من الـ host كـ fallback

### BUG: `curl -sf` مع `set -euo pipefail` يوقف الـ script
- **المشكلة:** `curl -sf` يرجع exit code 22 عند 4xx/5xx فيوقف الـ script بسبب pipefail
- **الحل:** استخدام `if RESP=$(curl -sf ...)` بدل direct pipe

### BUG: tool id يحتوي على `-` (hyphens)
- **المشكلة:** Open WebUI يرفض tool id بـ hyphens: `ai-company-tools` → 400 error
- **الحل:** استبدال بـ underscores: `ai_company_tools`

### BUG: `base_model` hardcoded في setup-openwebui.py
- **المشكلة:** `base_model = "openai/claude"` hardcoded
- **الحل:** يقرأ من `config/models.json` → `project_manager.model`

### FLOW النهائي للـ background setup
```
install.sh يخلص (~2 دقيقة)
    ↓
/tmp/ai-company-post-install.sh (background):
    1. ينتظر Infisical healthy (docker inspect + curl fallback)
    2. setup-infisical.py (ينشئ Machine Identity)
    3. infisical-sync.sh (لو credentials موجودة)
    4. setup-openwebui.py (admin + tools + project manager model)
    5. restart portainer + setup-portainer.py (admin)
    ↓
/var/log/ai-company-setup.log للمتابعة
```

---
---

## جلسة 2026-06-15 (مساء) — Agent Prompts + Infisical Timing

### BUG: GET /config/prompts في do_POST بدل do_GET
- **المشكلة:** endpoint الـ prompts أُضيف داخل `do_POST` handler فأرجع 404 للـ GET requests
- **الحل:** نقل الـ GET handler لـ `do_GET`

### BUG: Infisical setup يفشل بسبب timing
- **المشكلة:** sleep 90s + 180s wait = 270s لا يكفي في بعض الأنظمة
- **الحل:** loop ذكي يفحص `/api/status` كل 5 ثواني حتى 4 دقائق
- **سلوك جديد:** لو Infisical جاهز → يكمل الـ setup، لو لا → يُخبر المستخدم

### FEATURE: Agent Prompts قابلة للتعديل
- 8 agents: doc_analyzer, researcher, designer, planner, problem_solver, reviewer, project_manager, coder
- GET/POST /config/prompts في tools-api
- لوحة التحكم تعرض textarea لكل agent
- زر Save يحفظ في config/agent-prompts.json
- pipeline.py يقرأ منه تلقائياً

---
---

## جلسة 2026-06-15 — Fresh Install + Dashboard Improvements

### BUG: Infisical healthcheck endpoint خاطئ
- **المشكلة:** `setup-infisical.py` يستخدم `/api/v1/healthcheck` لكنه غير موجود
- **الحل:** تغيير للـ `/api/status` (الـ endpoint الصحيح في v1.0.0)

### BUG: ENCRYPTION_KEY طول خاطئ
- **المشكلة:** `openssl rand -hex 32` ينتج 64 حرف لكن Infisical يحتاج 32 حرف
- **الحل:** تغيير لـ `openssl rand -hex 16` (ينتج 32 حرف = 16 bytes)

### BUG: DNS لم يُضبط لـ flow.mkdd.nl
- **المشكلة:** "This site can't be reached" رغم أن NPM إعداداته صحيحة
- **الحل:** إضافة A record في DNS provider

### BUG: dashboard JS يستخدم hostname كـ API base مع الدومين
- **المشكلة:** `http://domain.com:9000` غير متاح من خارج الشبكة
- **الحل:** nginx proxy `/api/` → tools-api + JS يستخدم `/api` مع الدومين

### BUG: SyntaxError في loadCredentials (regex في onclick)
- **المشكلة:** `onclick="copyVal(this,'${v.replace(/\/g,...')}')"` يكسر HTML parser
- **الحل:** استخدام `data-val` attribute بدلاً من inline regex

### FEATURE: Infisical Setup Form في لوحة التحكم
- **المميزة:** المستخدم يدخل Machine Identity credentials مباشرةً من الـ dashboard
- **بدون terminal:** `POST /system/configure` يحفظ في .env ثم يشغّل sync تلقائياً

### Flow نهائي بعد التثبيت
1. `sudo bash install.sh --github-token TOKEN`
2. لوحة التحكم → Access Credentials → Show (لرؤية كل الـ credentials)
3. Infisical → Sign Up (بالـ credentials المولّدة)
4. Infisical → Machine Identity → Create → Copy ID + Secret
5. لوحة التحكم → Infisical Setup → أدخل الـ credentials → Save & Sync
6. Infisical → أضف API keys → لوحة التحكم → Sync Now

---
---

## جلسة 2026-06-14 — Install Script + Providers + Zero Hardcoded

### BUG: Arabic Unicode `──` في heredoc يلصق الأسطر
- **المشكلة:** الحرف `──` (U+2500) في comments الـ bash heredoc كان بيكوّل الأسطر
- **النتيجة:** `ANTHROPIC_API_KEY=` اتكتب على نفس سطر الـ comment، وأقسام كاملة اختفت
- **الحل:** استبدال heredoc بـ Python script (`update-env.py`) لكتابة الـ .env

### BUG: f-string مع newline في inline Python داخل bash heredoc
- **المشكلة:** `env += f"\n{k}={v}"` داخل `python3 - << CREDEOF` بيعطي SyntaxError
- **الحل:** نقل الكود لملف خارجي `secrets-sync/update-env.py`

### BUG: `INFISICAL_CLIENT_ID` مش بيتحفظ عند reinstall
- **المشكلة:** install.sh كان بيكتب .env من الصفر وبيمسح الـ credentials الموجودة
- **الحل:** `get_env()` function تقرأ القيمة الموجودة قبل الكتابة

### BUG: Providers مش بيظهروا في لوحة التحكم بعد install
- **المشكلة:** API keys فاضية في .env لأن sync مش اشتغل
- **الحل:** install.sh بيشغّل infisical-sync.sh أوتوماتيك بعد إعداد الـ credentials

### BUG: `generate_design_options` فشل بـ `{{...}}` double braces
- **المشكلة:** استخدام `{{key: value}}` في Python خارج f-string → `unhashable type: dict`
- **الحل:** إعادة كتابة الدالة كاملة بدون double braces

### BUG: litellm wildcard models مش مدعومة في v1.88.1
- **المشكلة:** `"anthropic/*"` في LiteLLM config لا تشتغل
- **الحل:** استخدام litellm كـ Python library مباشرة — يقرأ API keys من env تلقائياً

### BUG: OpenAI gpt-5.x لا يدعم `/v1/chat/completions`
- **المشكلة:** الموديلات الجديدة تستخدم `/v1/responses` API
- **الحل:** litellm library يتعامل مع كل API تلقائياً بدون hardcoded logic

---
---

## السجل

## السجل

---

### BUG-001 — فشل تسجيل الدخول لـ Infisical (401 Unauthorized)

- **التاريخ:** 2026-06-12
- **الوصف:** سكربت المزامنة `sync.py` يرجع `401 Invalid credentials` عند محاولة تسجيل الدخول بالهوية الآلية.
- **السبب:** Client Secret أُدخل بشكل ناقص أو غير صحيح (نُسخ يدوياً بسبب عدم عمل زر النسخ).
- **الحل المطبّق:** إنشاء Client Secret جديد في Infisical وإدخاله يدوياً بعناية. تصحيح `.env` بحذف القيم القديمة الخاطئة وإضافة القيم الصحيحة.
- **ملاحظة:** السبب الجذري لمشكلة النسخ هو أن Clipboard API لا تعمل على HTTP. الحل المؤقت: تفعيل `chrome://flags/#unsafely-treat-insecure-origin-as-secure`. الحل الدائم: إضافة HTTPS (مخطّط).

---

### BUG-009 — OpenHands runtime: docker.all-hands.ai غير موجود

- **التاريخ:** 2026-06-12
- **الوصف:** `docker.all-hands.ai` لا يمكن حل اسمه (NXDOMAIN) — OpenHands لا يستطيع تحميل runtime image.
- **الحل المطبّق:**
  1. نسخ source code من داخل OpenHands container.
  2. بناء runtime image محلي (`openhands-runtime-local:0.38`) بدون micromamba الكامل.
  3. ضبط `SANDBOX_RUNTIME_CONTAINER_IMAGE=openhands-runtime-local:0.38`.
  4. ضبط `SANDBOX_CONTAINER_NETWORK=ai-company_ai-company-net` لحل مشكلة الشبكة.
- **النتيجة:** runtime container يشتغل بنجاح.

---

### BUG-007 — GitHub Token لا يملك صلاحية إنشاء ريبوهات

- **التاريخ:** 2026-06-12
- **الوصف:** `403 Resource not accessible by personal access token` عند محاولة إنشاء ريبو.
- **السبب:** التوكن كان Fine-grained بدون صلاحية إنشاء مستودعات.
- **الحل المطبّق:** استبدال التوكن بـ Classic Token بصلاحية `repo` كاملة.

---

### BUG-008 — OpenHands API format خاطئ (422)

- **التاريخ:** 2026-06-12
- **الوصف:** `422 Unprocessable Entity` عند POST إلى `/api/conversations`.
- **السبب:** الـ payload كان يستخدم `{"task": ...}` أو `{"repository": ...}` — والصحيح هو `{"initial_user_msg": ...}`.
- **الحل المطبّق:** تحديث tools-api لاستخدام `initial_user_msg` مع الـ repo URL مضمّناً في نص المهمة.

---

### BUG-006 — Docker volume يتجدد بملكية root عند كل force-recreate

- **التاريخ:** 2026-06-12
- **الوصف:** `openhands_state` volume يعود لملكية root بعد كل `--force-recreate`.
- **السبب:** Docker volumes تُنشأ بملكية root افتراضياً. `force-recreate` يتجاهل الـ `chown` السابق.
- **الحل المطبّق:** تحويل الـ volume إلى bind mount على `/opt/ai-company/data/openhands-state` (مجلد على الـ host). المجلد يُنشأ مع `chown 1000:1000` في `install.sh` مرة واحدة ولا يتغير.
- **الملفات المعدَّلة:** `infrastructure/docker-compose.yml`، `install.sh`.


---

### BUG-005 — OpenHands: Permission denied على /.openhands-state

- **التاريخ:** 2026-06-12
- **الوصف:** `PermissionError: [Errno 13] Permission denied: '/.openhands-state/.jwt_secret'` — OpenHands يتعطّل عند بدء التشغيل.
- **السبب:** OpenHands يحتاج كتابة ملفات الحالة (JWT secret وغيره) في `/.openhands-state/`، والمسار غير موجود أو غير قابل للكتابة داخل الحاوية.
- **الحل المطبّق:** إضافة volume `openhands_state:/.openhands-state` + تشغيل `chown -R 1000:1000` على الـ volume لتصحيح الملكية لـ `uid 1000` (المستخدم الذي يعمل به OpenHands).
- **تحديث BUG-005:** السبب الحقيقي هو أن الـ volume يُنشأ بملكية `root:root` (755) وOpenHands يعمل بـ `uid 1000`. الحل الصحيح: تشغيل `chown -R 1000:1000` على الـ volume قبل تشغيل الكونتينر.


---

### BUG-004 — OpenHands يفشل بسبب غياب /var/run/docker.sock

- **التاريخ:** 2026-06-12
- **الوصف:** `stat: cannot statx '/var/run/docker.sock': No such file or directory` — OpenHands يُعيد التشغيل باستمرار.
- **السبب:** entrypoint الخاص بـ OpenHands يتحقق صراحةً من وجود ملف `docker.sock` بغض النظر عن `DOCKER_HOST`.
- **الحلول المجرَّبة والفاشلة:** `DOCKER_HOST=tcp://ai-openhands-dind:2375` وحده — فشل لأن الـ entrypoint يتحقق من الملف لا من المتغيّر.
- **الحل المطبّق:** إضافة `openhands-socat` كجسر: يستمع على Unix socket في volume مشترك ويحوّل الاتصالات لـ DinD عبر TCP. الـ VM محمي تماماً.

---

### BUG-003 — git pull يفشل عند تمرير التوكن في الـ URL

- **التاريخ:** 2026-06-12
- **الوصف:** `fatal: URL rejected: Malformed input to a URL function` أو `https://https://` عند استخدام `git pull "https://$TOKEN@github.com/..."`.
- **السبب:** التوكن يُنسخ مع أحرف إضافية أو يحتوي على رموز تُكسر ترميز الـ URL عند تضمينه فيه.
- **الحلول المجرَّبة والفاشلة:** تضمين التوكن مباشرة في رابط git — فشل بسبب ترميز الـ URL.
- **الحل المطبّق:** تجاوز git pull تماماً واستخدام `curl` مع التوكن في الـ HTTP header بدلاً من الـ URL، أو كتابة محتوى الملف مباشرة عبر heredoc. تم إنشاء `update.sh` كحل دائم.

---


---

### BUG-002 — خطأ في صيغة أمر git pull (https:// مزدوجة)

- **التاريخ:** 2026-06-12
- **الوصف:** `fatal: unable to access 'https://https://github.com/...'`
- **السبب:** لصق الرابط الكامل بدلاً من التوكن فقط في خانة إدخال GitHub Token.
- **الحل المطبّق:** تجاوز المشكلة لأن الملفات كانت موجودة بالفعل. التوكن الصحيح هو النص بعد `github_pat_` أو `ghp_` فقط بدون أي رابط.

---
