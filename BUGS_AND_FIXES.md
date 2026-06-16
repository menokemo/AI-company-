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
