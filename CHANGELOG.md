## [1.5.0] — 2026-06-16 — Critical Fixes + Auto Project Manager

### إصلاحات فورية
- **Agent Prompts**: 6/6 agents موصولين بـ `agent-prompts.json`
- **GIT_USERNAME**: يُجلب تلقائياً من GitHub API
- **Sync exit code**: يرجع 0 دائماً لو الاتصال نجح
- **Root check**: يُتجاهل داخل Docker containers

### جديد
- **🤖 إنشاء مدير المشروع**: زر يظهر بعد حفظ الموديلات
- **⚠️ TTL Warning**: تذكير بتجديد Client Secret كل 90 يوم
- **/setup/project-manager** endpoint في tools-api

---

## [1.4.0] — 2026-06-16 — Infisical Setup Wizard

### جديد
- **Infisical Setup Wizard** — دليل تفاعلي بـ 6 خطوات في لوحة التحكم
  - خطوة ١: Sign Up بالـ credentials المولّدة (قابلة للنسخ)
  - خطوة ٢: إنشاء Project
  - خطوة ٣: إنشاء Machine Identity
  - خطوة ٤: تفعيل Universal Auth + تحذير الـ Client ID الصح
  - خطوة ٥: إضافة Identity للـ Project + Project ID من الـ URL
  - خطوة ٦: إدخال الـ credentials + Save & Sync

### إصلاحات
- docker-cli في tools-api Dockerfile — sync يقدر يعمل docker restart
- ENV_FILE constant في server.py (كان NameError)
- HOST_IP default: `192.168.2.29` → `localhost`
- JS يعرض الـ sync output الحقيقي مش "undefined"

---

## [1.3.2] — 2026-06-16 — Dashboard Getting Started + Logo

### جديد
- **🚀 Getting Started** — قسم في لوحة التحكم بخطوات واضحة بعد التثبيت
- **MKDD Logo** — اللوجو في الـ header بتاع لوحة التحكم

---

## [1.3.1] — 2026-06-16 — Sync Button Fixes

### إصلاحات
- `/system/sync` + `/system/configure` نُقلوا لـ `do_POST`
- `/system/configure` يكتب الـ .env على disk
- tools-api Dockerfile: أضيف bash + curl
- `${BASH_SOURCE[0]}` → `$0` (Alpine compatibility)
- `INFISICAL_API_URL=http://ai-infisical:8080` في docker-compose
- Volumes: `.env` + `secrets-sync/` مـ mounted في tools-api
- Open WebUI tool id: `ai_company_tools` (لا hyphens)

---

## [1.3.0] — 2026-06-16 — Background Setup + Fast Install

### التغيير الكبير: Install يخلص في دقيقتين
- كل الـ setup (Infisical + OpenWebUI + Portainer) انتقل لـ background script
- `/var/log/ai-company-setup.log` للمتابعة
- الـ install لا ينتظر Infisical بعد الآن

### إصلاحات
- `docker compose wait` → `docker inspect` (healthcheck صح)
- `curl -sf` في loop → `if RESP=$(curl ...)` (pipefail آمن)
- `wget` في Infisical healthcheck (curl غير موجود في container)
- tool id: `ai-company-tools` → `ai_company_tools`
- base_model: hardcoded → يقرأ من `config/models.json`

### Flow المستخدم بعد التثبيت
```
١. لوحة التحكم → Access Credentials → Show
٢. Infisical → Sign Up → Machine Identity
٣. لوحة التحكم → Infisical Setup → Save & Sync
٤. Infisical → أضف API keys → Sync Now
٥. لوحة التحكم → موديلات المنظومة → اختار موديل → Save
٦. python3 setup-openwebui.py (لإنشاء مدير المشروع)
```

---

## [1.2.0] — 2026-06-15 — Agent Prompts Editor

### جديد
- **Agent Prompts Editor** في لوحة التحكم — تعديل prompt كل agent بدون كود
- 8 agents: doc_analyzer, researcher, designer, planner, problem_solver, reviewer, project_manager, coder
- `/config/prompts` GET+POST endpoints
- `pipeline.py` يقرأ الـ prompts من `config/agent-prompts.json`

### إصلاحات
- Infisical timing: smart wait loop (فحص كل 5 ثواني × 48 = 4 دقائق)
- GET /config/prompts كان في do_POST → نُقل لـ do_GET

---

## [1.1.0] — 2026-06-15 — Fresh Install Complete

### إصلاحات
- Infisical healthcheck: `/api/v1/healthcheck` → `/api/status`
- ENCRYPTION_KEY: 64 chars → 32 chars (openssl rand -hex 16)
- SyntaxError في credentials section (regex في onclick)
- Nginx proxy `/api/` للـ domain access

### جديد
- **Infisical Setup Form** في لوحة التحكم — بدون terminal
- `/system/configure` endpoint في tools-api
- `checkService` متوافق مع كل المتصفحات (AbortController بدل AbortSignal.timeout)

---

## [1.0.0] — 2026-06-14 — نظام التثبيت الكامل

### الإنجاز الكبير: تثبيت بأمر واحد
```bash
sudo bash install.sh --github-token ghp_xxx
```

### ما يحدث أوتوماتيك
1. Clone الريبو الخاص
2. توليد كل الـ secrets (random, secure)
3. كتابة .env بـ Python (تجنب encoding issues)
4. حفظ القيم الموجودة عند reinstall
5. تشغيل 12 خدمة Docker
6. إعداد Infisical + Machine Identity
7. Sync من Infisical (API keys, tokens)
8. ربط GitHub بـ OpenHands
9. عرض ملخص كامل

### صفر hardcoded في الكود
- litellm library يقرأ API keys من env تلقائياً
- docker-compose: `env_file: .env` في كل service
- models.json: فارغ، يُملأ من لوحة التحكم
- HOST_IP: يُكتشف من `hostname -I`

### Mockup Generation يعمل
- 3 تصميمات HTML مختلفة (modern, vibrant, professional)
- تُولَّد من `/config/providers` API
- تُعرض للمستخدم في Open WebUI قبل البدء

### Provider/Model Selection ديناميكي
- يجيب كل الموديلات من API كل مزوّد
- يعرض المزوّدين حتى لو غير مُهيَّأين

---

# سجل التغييرات — CHANGELOG

> كل تغيير مهم في المشروع يُسجَّل هنا، الأحدث في الأعلى.
> الصيغة مبنية على [Keep a Changelog](https://keepachangelog.com/).

---

## [غير منشور]

### قيد التخطيط
- المبرمج `OpenHands` (مكوّن داخلي).
- خط الوكلاء `CrewAI` + تكامل GitHub لإنشاء ريبو لكل مشروع.

---

## [0.29.0] — Install Script كامل + صفر hardcoded

### install.sh الجديد
- يأخذ `--github-token` فقط كـ input
- يولّد كل الـ secrets تلقائياً (random): LITELLM_MASTER_KEY, WEBUI_SECRET_KEY, DB passwords, JWT secrets
- يكتبها في `.env`
- يشغّل كل الخدمات
- يربط GitHub بـ OpenHands تلقائياً
- يعرض ملخص كامل مع الخطوات التالية

### صفر hardcoded
- docker-compose: `env_file: .env` في كل service
- litellm library: يقرأ API keys من env تلقائياً
- AGENT_SERVER_IMAGE_TAG: من .env (قابل للتغيير من Infisical)

### الخطوات اليدوية بعد التثبيت (مرة واحدة)
1. Infisical: إضافة API keys الخارجية
2. OpenHands Settings: إعداد LLM
3. لوحة التحكم: اختيار موديلات Crew

---

## [0.28.0] — Mockups + Sync كامل للريبو

### Mockup Generation يعمل ✅
- 3 تصميمات HTML (modern, vibrant, professional) تُولَّد من الـ designer agent
- تُخزَّن في `/opt/ai-company/config/mockups/`
- متاحة عبر `http://HOST_IP:9000/mockups/{id}`

### إصلاحات جوهرية
- BUG: `{{...}}` double braces في `generate_design_options` → fixed
- BUG: Anthropic model name غلط (`claude-sonnet-4-5-20251022` → `claude-sonnet-4-6`)
- BUG: HOST_IP=192.168.2.29 hardcoded → `${HOST_IP}` من .env

### Sync الريبو مع الـ VM
- `docker-compose.yml`: نسخة كاملة ومحدّثة تعكس الواقع الحالي
- `install.sh`: يشمل كل الخدمات الجديدة + HOST_IP تلقائي + GitHub setup

### ملاحظة مهمة بعد التثبيت
1. OpenHands Settings → LLM → أضف profile مرة واحدة
2. لوحة التحكم → اختر موديل لكل موظف من Crew Pipeline

---

## [0.27.0] — إضافة CrewAI Pipeline متكامل

### الموظفون الجدد (6 agents)
كل موظف له موديل مستقل يُعدَّل من Infisical:
- 📄 **محلل نصوص** (`AGENT_DOC_ANALYZER_MODEL`) — يستخرج البنية الهرمية من أي مستند
- 🔍 **باحث** (`AGENT_RESEARCHER_MODEL`) — best practices + tech stack
- 🎨 **مصمم** (`AGENT_DESIGNER_MODEL`) — هيكل المشروع + UI/UX
- 📋 **مخطط** (`AGENT_PLANNER_MODEL`) — خطة تقنية مفصّلة للتنفيذ
- 🔧 **حلّال مشاكل** (`AGENT_SOLVER_MODEL`) — يراجع الخطة ويحل التعارضات
- 👁️ **مراجع** (`AGENT_REVIEWER_MODEL`) — جودة + أمان + معايير القبول

### Pipeline التسلسلي
doc_analyzer → researcher → designer → planner → problem_solver → reviewer → OpenHands

### ملفات جديدة
- `crew-service/crew.py` — HTTP service + pipeline runner
- `crew-service/agents.py` — تعريف الموظفين
- `crew-service/tasks.py` — تعريف المهام والـ context flow
- `crew-service/Dockerfile`

### تحديثات
- `docker-compose.yml`: crew-service على بورت 9002
- `tools-api/server.py`: يستدعي crew-service بدلاً من OpenHands مباشرة

---

## [0.26.0] — المنظومة تعمل بالكامل ✅

### المنجزات
- **OpenHands V1** يكتب كود حقيقي ويدفعه على GitHub
- **GitHub Integration** أوتوماتيك من Infisical عبر `/api/v1/secrets/git-providers`
- **Workflow احترافي:** الكود يُدفع على branch جديد (مش main)
- **tools-api:** `git_provider: "github"` + تعليمات push واضحة

### Workflow النهائي
Open WebUI → مدير المشروع → create_project → GitHub repo → OpenHands → branch → PR → main

### ملاحظة
إعداد LLM في OpenHands Settings يُعمل مرة واحدة بعد التثبيت.

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
