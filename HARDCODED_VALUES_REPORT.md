# 🚨 تقرير الـ Hardcoded Values في منظومة AI Company

**التاريخ:** 2026-06-18  
**الإصدار:** v1.7.0  
**الخطورة:** ⚠️ متوسطة إلى عالية

---

## 📊 **الملخص السريع**

| النوع | العدد | الخطورة |
|-------|-------|---------|
| **Localhost/Default URLs** | 15+ | 🟡 متوسط |
| **Hardcoded Paths** | 10+ | 🟡 متوسط |
| **Ports** | 12+ | 🟡 متوسط |
| **Organization Names** | 3 | 🟢 منخفض |
| **API Endpoints** | 5+ | 🟢 منخفض |

**الإجمالي:** 45+ hardcoded values

---

## 🔴 **المشاكل الحرجة**

### 1. **Hardcoded Paths (⚠️ متوسط)**

```python
# في multiple files:
"/opt/ai-company/infrastructure/.env"
"/opt/ai-company/data/openhands-state"
"/opt/ai-company/data/openhands"
"/opt/workspace"
```

**الملفات المتأثرة:**
- `tools-api/server.py` (2 مرات)
- `secrets-sync/setup-infisical.py`
- `secrets-sync/setup-portainer.py`
- `secrets-sync/write-env.py`
- `secrets-sync/update-env.py`
- `secrets-sync/generate-openhands-config.py`
- `crew-service/crew.py`
- `bootstrap.sh`
- `update.sh`
- `infisical-sync.sh`

**المشكلة:** إذا تغيير مكان التثبيت من `/opt/ai-company` لأي مكان آخر، كل هذه الملفات محتاج تعديل يدوي!

**الحل المقترح:**
```python
# بدل:
ENV_FILE = "/opt/ai-company/infrastructure/.env"

# استخدم:
ENV_FILE = os.environ.get("INSTALL_DIR", "/opt/ai-company") + "/infrastructure/.env"
# أو أفضل:
INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")
```

---

### 2. **Localhost/Default URLs (⚠️ متوسط)**

```python
# الـ defaults:
"http://localhost:8080"    # Infisical
"http://localhost:8888"    # Open WebUI
"http://localhost:3000"    # OpenHands
"http://localhost:9443"    # Portainer
"https://localhost:9443"   # Portainer (HTTPS)
"http://ai-tools-api:9000"          # Docker network
"http://ai-openhands:3000"          # Docker network
"http://ai-crew:9002"               # Docker network
"http://ai-litellm:4000"            # Docker network
```

**الملفات المتأثرة:**
- `tools-api/server.py` (3 مرات)
- `tools-api/openwebui_tools.py`
- `secrets-sync/sync.py`
- `secrets-sync/setup-infisical.py`
- `secrets-sync/setup-openwebui.py`
- `secrets-sync/setup-portainer.py`
- `secrets-sync/infisical-sync.sh`
- `crew-service/crew.py` (2 مرات)
- `start-page/index.html` (3 مرات)

**المشكلة:**
- في الـ development: يفترض localhost
- في الـ production: قد لا تعمل على server آخر
- لا وضوح عن البيئة الفعلية

**الحل المقترح:**
```python
# بدل:
INFISICAL_URL = "http://localhost:8080"

# استخدم:
INFISICAL_URL = os.environ.get("INFISICAL_URL", "http://ai-infisical:8080")
```

---

### 3. **Organization/Project Names (🟢 منخفض)**

```python
# في setup-infisical.py:
"AI Company"           # Organization name
"ai-company"          # Workspace name
"auto-generated"      # Description

# في infisical-sync.sh:
OPENHANDS_STATE_DIR="/opt/ai-company/data/openhands-state"
```

**المشكلة:** اسم المنظمة مكتوب يدويًا، قد يكون مربك للمستخدمين الذين يريدون تغيير الاسم.

**الحل:**
```python
ORG_NAME = os.environ.get("ORG_NAME", "AI Company")
WORKSPACE_NAME = os.environ.get("WORKSPACE_NAME", "ai-company")
```

---

### 4. **API Endpoints (🟢 منخفض)**

```python
# في server.py:
"https://api.anthropic.com/v1/models"
"https://api.openai.com/v1/models"
"https://openrouter.ai/api/v1/models"
"https://api.github.com/user"
"https://api.github.com/user/repos"
"https://api.github.com/repos/{user}/{repo}"
```

**المشكلة:** تغيير API endpoints ممكن لكن محتاج تعديل الكود مباشرة.

**الحل:**
```python
PROVIDERS = {
    "anthropic": {
        "url": os.environ.get("ANTHROPIC_MODELS_URL", "https://api.anthropic.com/v1/models"),
        ...
    }
}
```

---

## 📋 **قائمة كاملة الـ Hardcoded Values**

### في `tools-api/server.py`:

```python
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")  # ✅ متغير
CREW_URL = os.environ.get("CREW_URL", "http://ai-crew:9002")  # ✅ متغير
ENV_FILE = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")  # ⚠️ path hardcoded
HOST_IP = os.environ.get("HOST_IP", "localhost")  # ✅ متغير

# Hardcoded في الـ API calls:
"http://localhost:8080"  # Infisical (default)
"http://localhost:8888"  # Open WebUI (default)
"https://localhost:9443"  # Portainer (default)
"http://localhost:4000"   # LiteLLM (default)
```

### في `crew-service/crew.py`:

```python
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")  # ✅
LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")  # ✅
ENV_FILE = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")  # ⚠️
```

### في `secrets-sync/` scripts:

```bash
# infisical-sync.sh:
INFISICAL_API_URL="${INFISICAL_API_URL:-http://localhost:8080}"  # ✅ متغير مع default
OH_HOST="http://localhost:3000"  # ⚠️ hardcoded
OPENHANDS_STATE_DIR="/opt/ai-company/data/openhands-state"  # ⚠️ path hardcoded

# setup-infisical.py:
BASE = os.environ.get("INFISICAL_API_URL", "http://localhost:8080")  # ✅
ENV_FILE = "/opt/ai-company/infrastructure/.env"  # ⚠️ hardcoded
```

### في `start-page/index.html`:

```javascript
// في JavaScript:
'http://' + host + ':9000'  // ✅ dynamic (جيد!)
'http://'+host+':8080'       // ✅ dynamic
'http://'+host+':8888'       // ✅ dynamic
```

---

## 🎯 **الأولويات والحلول**

### Priority 1 (حرج - لازم الآن):

#### 1. تقييس الـ Paths
```bash
# استخدم متغير واحد في كل مكان:
INSTALL_DIR="/opt/ai-company"

# بدل كتابة الـ path كاملة في كل ملف
```

**الملفات المتأثرة:**
- ✅ `tools-api/server.py`
- ✅ `crew-service/crew.py`
- ✅ `secrets-sync/*.py`
- ✅ `infisical-sync.sh`

---

#### 2. موحدة الـ URLs (Docker Network vs Localhost)

```bash
# في docker-compose.yml أضيف:
services:
  ai-tools-api:
    environment:
      - OPENHANDS_URL=http://ai-openhands:3000  # Docker network
      - CREW_URL=http://ai-crew:9002
      - LITELLM_URL=http://ai-litellm:4000
      
  # للـ localhost fallback:
    environment:
      - OPENHANDS_URL=${OPENHANDS_URL:-http://ai-openhands:3000}
```

---

### Priority 2 (مهم - الأسبوع القادم):

#### 1. إنشاء `.env` template موحدة

```env
# installation
INSTALL_DIR=/opt/ai-company
ORG_NAME=AI Company

# URLs - Docker Network (production)
OPENHANDS_URL=http://ai-openhands:3000
CREW_URL=http://ai-crew:9002
LITELLM_URL=http://ai-litellm:4000
INFISICAL_URL=http://ai-infisical:8080
OPENWEBUI_URL=http://ai-open-webui:8888
PORTAINER_URL=https://ai-portainer:9443

# URLs - Localhost (development)
# OPENHANDS_URL=http://localhost:3000
# CREW_URL=http://localhost:9002
# LITELLM_URL=http://localhost:4000
```

---

#### 2. تحديث كل الـ Python files

```python
# Pattern موحدة:
INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
CREW_URL = os.environ.get("CREW_URL", "http://ai-crew:9002")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://ai-litellm:4000")
```

---

### Priority 3 (اختياري - المستقبل):

#### 1. Config file بدل environment variables
```python
# بدل:
import os
URL = os.environ.get("URL", "default")

# استخدم:
import json
with open("config.json") as f:
    config = json.load(f)
URL = config.get("url", "default")
```

---

## 📋 **Checklist للإصلاح**

### Phase 1: Paths (يوم واحد)
- [ ] إنشاء متغير `INSTALL_DIR` في كل file
- [ ] تحديث `tools-api/server.py`
- [ ] تحديث `crew-service/crew.py`
- [ ] تحديث `secrets-sync/*.py`
- [ ] تحديث `infisical-sync.sh`

### Phase 2: URLs (يومان)
- [ ] إنشاء `.env.example` محدثة
- [ ] تحديث docker-compose.yml
- [ ] تحديث كل الـ Python files
- [ ] تحديث الـ Bash scripts
- [ ] تحديث `install.sh`

### Phase 3: Documentation (نصف يوم)
- [ ] تحديث README
- [ ] إضافة configuration guide
- [ ] توثيق الـ environment variables

---

## 🔒 **الأمان - هل هناك مشاكل أمنية؟**

### ✅ ما هو آمن:
- API URLs عام (ليس secrets)
- Localhost defaults آمنة للـ development
- Ports موثقة بشكل واضح

### ⚠️ ما يحتاج انتباه:
- لا توجد secrets مكتوبة بشكل مباشر ✅ (جيد!)
- لا توجد API keys hardcoded ✅ (جيد!)
- لا توجد passwords hardcoded ✅ (جيد!)

**الخلاصة:** لا توجد مشاكل أمنية حقيقية، لكن **flexibility** هي المشكلة الرئيسية.

---

## 🎯 **الخلاصة**

| المشكلة | الشدة | التأثير | الحل |
|--------|-------|---------|------|
| Hardcoded paths | 🟡 | عالي | استخدام `INSTALL_DIR` variable |
| Localhost URLs | 🟡 | متوسط | استخدام environment variables |
| Organization names | 🟢 | منخفض | جعلها في environment variables |
| API endpoints | 🟢 | منخفض | جعلها في config file |

---

## 📝 **توصياتي:**

1. **فوراً:** وحدّ الـ paths باستخدام `INSTALL_DIR`
2. **قريب:** استخدم `.env` موحدة لجميع الـ URLs
3. **مستقبل:** فكر في config file بدل environment variables

**الأثر الكلي على المنظومة:** 🟡 **متوسط** - لن يؤثر على الأمان، لكن سيحسّن الـ flexibility والـ portability.

---

**تم إعداد التقرير:** 2026-06-18  
**الحالة:** ⚠️ بحاجة للإصلاح

