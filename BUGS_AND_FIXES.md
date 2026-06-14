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
