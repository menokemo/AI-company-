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
