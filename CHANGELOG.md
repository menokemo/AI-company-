# سجل التغييرات — CHANGELOG

> كل تغيير مهم في المشروع يُسجَّل هنا، الأحدث في الأعلى.
> الصيغة مبنية على [Keep a Changelog](https://keepachangelog.com/).

---

## [غير منشور]

### قيد التخطيط
- المبرمج `OpenHands` (مكوّن داخلي).
- خط الوكلاء `CrewAI` + تكامل GitHub لإنشاء ريبو لكل مشروع.

---

## [0.25.0] — GitHub push أوتوماتيك من Infisical

### المشكلة
agent-server كان يكتب الكود لكن لا يدفعه لـ GitHub (لا credentials).

### الحل
إضافة `SANDBOX_ENV_GITHUB_TOKEN` و `SANDBOX_ENV_GIT_USERNAME` في docker-compose.yml — تُقرأ من `.env` (المتزامن مع Infisical) وتُمرَّر لكل agent-server تلقائياً.

---

## [0.24.0] — OpenHands يعمل ✅ (بعد 3 أيام!)

### الحل النهائي
- **المشكلة الجذرية:** OpenHands غيّر معمارتها بالكامل (V0→V1 نوفمبر 2025). الـ image القديم (`all-hands-ai`) لم يعد يعمل.
- **الحل:** `ghcr.io/openhands/openhands:latest` + `ghcr.io/openhands/agent-server:1.25.0-python`.
- **إعداد LLM:** `model=openai/claude`, `base_url=http://HOST_IP:4000` (لا `ai-litellm` لأن agent-server خارج الـ Docker network).
- **الإعداد عبر Settings UI** — لا env vars — هي الطريقة الوحيدة المدعومة في V1.

### تحديث الملفات
- `docker-compose.yml`: OpenHands V1 بدون SANDBOX_RUNTIME_CONTAINER_IMAGE.
- `generate-openhands-config.py`: يولّد `config.toml` بـ `openai/claude` + IP الـ VM تلقائياً.
- `install.sh`: يحمّل agent-server image مسبقاً + يجهّز المجلدات.

### ملاحظة مهمة بعد التثبيت
بعد أول تشغيل: افتح OpenHands (:3000) → Settings → LLM → أضف profile جديد:
- Name: litellm
- Custom Model: openai/claude
- Base URL: http://VM_IP:4000
- API Key: LITELLM_MASTER_KEY
ثم Save Changes. هذا الإعداد يُحفظ تلقائياً في كل المحادثات التالية.

---

## [0.23.0] — code-writer يستبدل OpenHands للكتابة التلقائية

### قرار
- استبدال الاعتماد على OpenHands runtime بـ `code-writer` — خدمة بسيطة تستدعي Claude مباشرة وترفع الكود على GitHub.
- OpenHands يبقى متاحاً للمستخدم يدوياً على :3000 للتعديلات والتكرار.

### أُضيف
- `code-writer/writer.py`: يستقبل وصف المشروع → يطلب من Claude الكود كاملاً → يرفعه على GitHub عبر API.
- `code-writer/Dockerfile`: حاوية بسيطة بدون dependencies خارجية.
- `tools-api`: تحدّث لاستخدام `code-writer` بدل OpenHands API.

### النتيجة
المشروع يُكتب ويُرفع على GitHub تلقائياً بدون runtime containers أو تعقيدات.

---

## [0.22.0] — OpenHands runtime يشتغل ✅

### اكتمل (BUG-009)
- بناء `openhands-runtime-local:0.38` محلياً من source code داخل OpenHands container.
- Runtime container يشتغل بنجاح باستخدام `openhands-runtime-local:0.38`.
- الشبكة مضبوطة: `SANDBOX_CONTAINER_NETWORK=ai-company_ai-company-net`.

### الآن المنظومة تعمل كاملاً:
1. Open WebUI → مدير المشروع AI يناقشك
2. tools-api → ينشئ GitHub repo
3. OpenHands API → ينشئ conversation
4. Runtime container → يكتب الكود فعلاً
5. الكود يُحفظ على GitHub

---

## [0.21.0] — المنظومة تعمل end-to-end ✅

### اكتمل
- GitHub repo ينشأ تلقائياً عند بدء مشروع جديد.
- OpenHands يستقبل المهمة تلقائياً عبر `/api/conversations`.
- الـ flow الكامل: Open WebUI → tools-api → GitHub + OpenHands.

### إصلاحات
- BUG-007: استبدال Fine-grained token بـ Classic token (صلاحية `repo`).
- BUG-008: تصحيح OpenHands API format إلى `initial_user_msg`.
- تبسيط tools-api/server.py وإزالة الكود القديم.

---

## [0.20.0] — Tool Calls API + System Prompt

### أُضيف
- `tools-api/server.py`: خدمة Python بسيطة (بدون مكتبات خارجية) تتيح:
  - `POST /create-repo`: إنشاء GitHub repo.
  - `POST /start-coding`: تشغيل OpenHands بمهمة.
  - `POST /create-and-start`: الاثنان معاً.
  - `GET /health`: فحص الحالة.
- `tools-api/system-prompt.md`: System Prompt بالعربي لمدير المشروع (٥ مراحل).
- إضافة `tools-api` كخدمة في `docker-compose.yml`.
- تمرير `GITHUB_TOKEN` و `GIT_USERNAME` لـ Open WebUI و tools-api.

---

## [0.19.0] — Open WebUI (واجهة الشات الرئيسية)

### أُضيف
- `open-webui`: واجهة شات متكاملة، موصّلة بـ LiteLLM تلقائياً، على البورت `8888`.
- `WEBUI_SECRET_KEY` يُولَّد تلقائياً في `install.sh`.
- تحديث لوحة التحكم: رابط Open WebUI هو أول بطاقة (نقطة الدخول الرئيسية).

---

## [0.18.0] — قرار معماري: Open WebUI بديلاً عن CrewAI

### قرار مهم
- **إلغاء:** CrewAI و ٥ وكلاء منفصلين.
- **البديل:** `Open WebUI` كواجهة شات + AI بدور "مدير مشروع" واحد بمراحل واضحة.

### السبب
CrewAI مناسب للأتمتة الكاملة. المستخدم يريد نقاشاً تفاعلياً وتعديلات لحظية — محادثة واحدة ذكية أسرع وأبسط وأكثر ملاءمة لـ vibe coding.

### خط العمل الجديد
فكرة المستخدم ← نقاش ← مواصفات ← خطة تقنية ← Tool Call (GitHub repo + OpenHands) ← كود ← تعديلات من نفس الشات.

### الأدوات القادمة
- `Open WebUI`: واجهة الشات self-hosted على البورت `8888`.
- `Tool Calls API`: خدمة Python بسيطة تربط الشات بـ GitHub و OpenHands.
- System Prompt مخصّص بالعربية لمدير المشروع.

---

## [0.17.0] — إصلاح نهائي لـ OpenHands + Git credentials

### إصلاح BUG-006 (نهائي)
- `docker-compose.yml`: bind mount دائم لـ `/.openhands-state` بدل Docker volume.
- `install.sh`: ينشئ `/opt/ai-company/data/openhands-state` بملكية `uid 1000` مرة واحدة.

### أُضيف
- `generate-openhands-config.py`: يولّد `.git-credentials` و `.gitconfig` داخل مجلد الـ state.
- `infisical-sync.sh`: يعيد تشغيل OpenHands تلقائياً بعد كل sync.

### النتيجة
- OpenHands يبدأ بدون أي خطأ صلاحيات.
- Git credentials جاهزة داخل الحاوية من أول تشغيل.

---

## [0.16.0] — OpenHands يتكوّن تلقائياً بالكامل

### أُضيف
- `secrets-sync/generate-openhands-config.py`: يولّد `/.openhands-state/settings.json` تلقائياً من `.env` بعد كل sync.
- يتضمن: `llm_model`, `llm_base_url`, `llm_api_key`, `github_token`, `git_username`.
- `infisical-sync.sh` يستدعيه تلقائياً بعد كل مزامنة.

### النتيجة
لما تشتغل المنظومة أو تعمل sync:
1. Infisical → .env → settings.json → OpenHands
2. OpenHands يشتغل بدون أي dialog أو إعداد يدوي.

---

## [0.15.0] — لوحة التحكم + Auto-sync

### أُضيف
- `start-page/index.html`: لوحة تحكم ويب بتعرض كل الخدمات مع حالتها الحية، روابط سريعة، أوامر نسخ، وحالة المشروع.
- `start-page/nginx.conf`: nginx بيخدم اللوحة على البورت `80`.
- خدمة `start-page` في `docker-compose.yml`.
- **Auto-sync**: cron job كل ساعة يشغّل `infisical-sync.sh` تلقائياً — مضاف لـ `install.sh`.

### النتيجة
- لوحة التحكم: `http://IP` (البورت 80)
- المزامنة التلقائية: كل ساعة بدون تدخّل

---

## [0.14.0] — ربط OpenHands بـ Infisical

### إصلاح (مشكلة مشروعة)
- OpenHands كان يطلب إعداد يدوي للـ LLM و Git بدل ما يقرأ من البيئة.
- السبب: إعدادات OpenHands لم تكن مربوطة بـ Infisical مثل LiteLLM.

### تغيّر
- `LLM_MODEL` أصبح `openai/claude` (الصيغة الصحيحة لـ LiteLLM proxy).
- إضافة `GITHUB_TOKEN` و `GIT_USERNAME` في متغيّرات البيئة لـ OpenHands.
- تحديث `infisical-sync.sh`: يسحب `GITHUB_TOKEN` من Infisical مع باقي المفاتيح.
- النتيجة: OpenHands يتكوّن تلقائياً بدون أي dialog يدوي.

### الآن Infisical هو المصدر الوحيد لكل المفاتيح:
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` → LiteLLM ✅
- `GITHUB_TOKEN` → OpenHands + update.sh ✅

---

## [0.13.0] — OpenHands يعمل ✅

### اكتمل
- OpenHands يعمل على منفذ `3000` بدون أخطاء.
- جذر المشكلة: volume مُنشأ بملكية `root:root` (755) وOpenHands يعمل بـ `uid 1000`.
- الحل: `chown -R 1000:1000` على الـ volume قبل التشغيل.
- إضافة `external: true` للـ volume في compose لإلغاء تحذير Docker Compose.

---

## [0.12.0] — إصلاح BUG-005: OpenHands Permission Error

### إصلاح
- إضافة volume `openhands_state:/.openhands-state` — يحل خطأ الصلاحيات عند كتابة JWT secret.

---

## [0.11.0] — تبسيط المنظومة + تحديث تلقائي عبر Infisical

### تغيّر (تبسيط)
- حذف `openhands-dind` و `openhands-socat` (كانا يسبّبان تعقيداً غير ضروري).
- `openhands` يستخدم Docker socket مباشرةً (نفس أسلوب Portainer).
- حذف volumes غير مستخدمة: `dind_data`, `dind_socket`.

### أُضيف
- `secrets-sync/get_secret.py`: يجلب قيمة سرّ واحد من Infisical.
- `update.sh` (إعادة كتابة): يقرأ `GITHUB_TOKEN` من Infisical تلقائياً — لا إدخال يدوي. أمر واحد: `sudo bash /opt/ai-company/update.sh`.

### الآن لتحديث المنظومة
1. أضف `GITHUB_TOKEN` في Infisical (مرة واحدة).
2. `sudo bash /opt/ai-company/update.sh` — بدون أي إدخال.

---

## [0.10.0] — إصلاح OpenHands عبر socat bridge

### إصلاح (BUG-004)
- إضافة `openhands-socat`: جسر Alpine socat يحوّل DinD TCP إلى Unix socket في volume مشترك.
- `dind_socket` volume مشترك بين socat و openhands.
- healthcheck على socat يضمن جاهزية الـ socket قبل تشغيل openhands.

---

## [0.9.0] — OpenHands يعمل + سكربت تحديث دائم

### اكتمل
- OpenHands شغّال على المنفذ `3000` عبر DinD معزول.
- `openhands-dind` healthy، `openhands` started بنجاح.

### أُضيف
- `update.sh`: سكربت تحديث دائم يستخدم `curl` مع Authorization header بدلاً من تضمين التوكن في URL — يحل BUG-003 نهائياً.

### وُثِّق
- BUG-003: git pull يفشل بسبب ترميز التوكن في URL — حُلَّ بـ update.sh.

---

## [0.8.0] — طبقة OpenHands (المبرمج المعزول)

### أُضيف
- `openhands-dind`: Docker daemon معزول (Docker-in-Docker) يمنع OpenHands من لمس Docker الحقيقي للـ VM.
- `openhands`: المبرمج الذكي، يتصل بـ DinD (لا بـ VM)، مكوّن بـ LiteLLM كبوابة نماذج.
- إضافة volumes: `dind_data` و `openhands_workspace`.
- تحديث `.env.example` و `install.sh` بإضافة `DIND_IMAGE_TAG` و `OPENHANDS_IMAGE_TAG`.

### تفاصيل العزل الأمني
- OpenHands يتحدث لـ `tcp://ai-openhands-dind:2375` فقط — لا وصول لـ `/var/run/docker.sock` الحقيقي.
- أي containers ينشئها OpenHands تعيش داخل DinD معزولة تماماً عن المضيف.
- مساحة العمل محدودة بـ volume منفصل (`openhands_workspace`).
- sandbox يعمل بـ `SANDBOX_USER_ID=1000` (non-root).

---

## [0.7.0] — مزامنة Infisical مع LiteLLM تعمل بنجاح

### اكتمل
- المزامنة تعمل: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` تُسحب من Infisical وتُحقن في `LiteLLM` تلقائياً.
- `LiteLLM` يعيد تشغيله تلقائياً بعد كل مزامنة.
- بيانات الاتصال (`Machine Identity`) محفوظة في `.env` (محميّ 600).

### مشاكل وُثِّقت وحُلَّت
- BUG-001: Client Secret خاطئ (401) — حُلَّ بإنشاء سرّ جديد.
- BUG-002: صيغة git pull خاطئة — حُلَّت.
- Clipboard API لا تعمل على HTTP — حلّ مؤقت بـ Chrome flag، حلّ دائم (HTTPS) مخطّط.

---

## [0.6.0] — ربط Infisical بـ LiteLLM

### أُضيف
- `secrets-sync/sync.py`: يسحب الأسرار من Infisical عبر Machine Identity (Universal Auth) ويحدّث المفاتيح في `.env`.
- `secrets-sync/infisical-sync.sh`: سكربت ربط يطلب بيانات الاتصال مرة واحدة (إدخال مخفي للسرّ)، يزامن المفاتيح، ويعيد تشغيل `LiteLLM`.

### كيف يعمل
- `Infisical` يبقى مصدر الحقيقة الوحيد للمفاتيح.
- المزامنة تحقن `ANTHROPIC_API_KEY` و `OPENAI_API_KEY` و `OPENROUTER_API_KEY` في `.env` (محميّ، غير مرفوع)، ثم يُعاد تشغيل `LiteLLM`.
- لإعادة المزامنة بعد أي تعديل في Infisical: تشغيل نفس السكربت.

---

## [0.5.0] — دعم عدة مزوّدين

### أُضيف
- دعم `OpenAI` و `OpenRouter` بجانب `Anthropic` في بوابة `LiteLLM`.
- متغيّرات `OPENAI_API_KEY` و `OPENROUTER_API_KEY` في الإعداد و `.env`.

### ملاحظة
- كل المفاتيح تُخزَّن في `Infisical` (مكان واحد)، وتُحقَن في `LiteLLM` في طبقة الربط القادمة.

---

## [0.4.0] — الإقلاع بأمر واحد + سياسة عزل OpenHands

### أُضيف
- `bootstrap.sh`: إقلاع المنظومة بأمر واحد (تثبيت git، استنساخ المستودع، تشغيل المثبّت)، مع إدخال التوكن المخفي وإزالته من إعدادات git بعد الاستنساخ.
- قسم **عزل OpenHands (أمان حرج)** في `PROJECT_SUMMARY`.

### تغيّر
- قسم التشغيل في `README` أصبح أمرًا واحدًا: `sudo bash bootstrap.sh`.

### قرار أمني مُلزِم
- `OpenHands` سيعمل بمستخدم غير جذري، دون وصول إلى Docker socket المضيف أو صلاحيات الجذر، ومقيّدًا بمساحة عمله فقط — حتى لا يضرّ الـ VM.

---

## [0.3.0] — طبقة البنية التحتية

### أُضيف
- `install.sh`: سكربت تثبيت idempotent (يثبّت Docker، يولّد الأسرار، يرفع الخدمات).
- `infrastructure/docker-compose.yml`: `Portainer` + `Infisical` (+ Postgres + Redis) + `LiteLLM`.
- `infrastructure/.env.example`: قالب موثّق لكل القيم المطلوبة.
- `llm-gateway/config.yaml`: إعداد بوابة LiteLLM.

### تفاصيل الاستقرار
- `restart: unless-stopped` لكل الخدمات.
- `healthchecks` لقاعدة البيانات و Redis، مع `depends_on` بشرط الصحّة.
- تخزين دائم عبر `volumes`، وحدود ذاكرة لكل خدمة، وشبكة داخلية معزولة.
- الأسرار تُولّد محلياً في `.env` (محميّ 600، غير مرفوع للريبو).

---

## [0.2.0] — تصحيح المعمارية

### تغيّر
- توضيح أن `OpenHands` **مكوّن داخلي** (دور المبرمج) وليس أداة بناء المنظومة.
- المنظومة كلها تُبنى وتُسلَّم كاملة عبر **سكربت تثبيت** يشغّله المستخدم على الـ `VM`.

### أُضيف
- قرار: كل مشروع تنتجه المنظومة يُحفظ في **ريبو GitHub خاص به**، لا على السيرفر.
- قسم **مبادئ الكفاءة والاستقرار** في `PROJECT_SUMMARY`.
- مزايا جديدة في جدول الحالة: سكربت التثبيت، تكامل GitHub للمشاريع.

---

## [0.1.0] — التأسيس

### أُضيف
- هيكل المستودع الأساسي.
- `README.md` يشرح المنظومة ومكوّناتها وخط العمل.
- `PROJECT_SUMMARY.md` كمرجع شامل لحالة المشروع والمزايا.
- `CHANGELOG.md` لتتبّع التغييرات.
- `BUGS_AND_FIXES.md` لتوثيق المشاكل وحلولها.
- `.gitignore` لحماية الأسرار والملفات المؤقتة.
