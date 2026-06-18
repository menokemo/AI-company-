# 📋 خطة التنفيذ الآمنة: إزالة الـ Hardcoded Values

**الإصدار:** v1.7.0 → v1.7.1  
**المدة:** 3 مراحل × 3 أيام = 9 أيام  
**المخاطر:** منخفضة (مع اتباع الخطة)  

---

## 🎯 **الملخص السريع**

```
المرحلة 1: التحضير والتخطيط (اليوم 1-2)
المرحلة 2: التعديلات (اليوم 3-6)
المرحلة 3: الاختبار والـ Deployment (اليوم 7-9)
```

---

## 🔴 **المرحلة 1: التحضير (اليوم 1-2)**

### اليوم 1: التحضير البيئي

#### 1️⃣ عمل Backup كامل

```bash
# قبل أي حاجة، سجل الحالة الحالية:
cd /home/claude/repo

# 1. commit الحالة الحالية
git status
git add .
git commit -m "chore: snapshot before hardcoded refactoring"

# 2. إنشاء branch للـ backup
git branch backup-v1.7.0-before-refactor

# 3. إنشاء branch للـ work
git checkout -b refactor/remove-hardcoded-v1.7.1
```

#### 2️⃣ التحضير البيئي

```bash
# 1. إنشاء متغيرات البيئة المستخدمة:
export INSTALL_DIR="/opt/ai-company"
export ORG_NAME="AI Company"
export WORKSPACE_NAME="ai-company"

# 2. تجهيز ملف .env الجديد:
mkdir -p /tmp/refactor-backup
cp /opt/ai-company/infrastructure/.env /tmp/refactor-backup/.env.backup
```

#### 3️⃣ قائمة المهام

```bash
# طباعة قائمة المهام:
cat > /tmp/refactoring-checklist.txt << 'CHECKLIST'
PHASE 1: PREPARATION
======================
Day 1:
  ☐ git commit الحالة الحالية
  ☐ git branch backup-v1.7.0-before-refactor
  ☐ git checkout -b refactor/remove-hardcoded-v1.7.1
  ☐ backup .env files
  ☐ توثيق القيم الحالية

Day 2:
  ☐ مراجعة قائمة الملفات المتأثرة
  ☐ عمل جدول بأماكن التغييرات
  ☐ اختبار environment على clean system

PHASE 2: MODIFICATIONS
======================
Day 3:
  ☐ تعديل .env.example
  ☐ تعديل install.sh
  ☐ تعديل bootstrap.sh

Day 4:
  ☐ تعديل docker-compose.yml
  ☐ تعديل infrastructure scripts

Day 5:
  ☐ تعديل tools-api/server.py
  ☐ تعديل tools-api/openwebui_tools.py

Day 6:
  ☐ تعديل crew-service/crew.py
  ☐ تعديل جميع secrets-sync/*.py

PHASE 3: TESTING & DEPLOYMENT
==============================
Day 7:
  ☐ اختبار على نظام نظيف
  ☐ التحقق من جميع الـ paths
  ☐ اختبار docker-compose

Day 8:
  ☐ اختبار الـ services
  ☐ اختبار الـ API endpoints
  ☐ اختبار الـ Secrets loading

Day 9:
  ☐ commit نهائي
  ☐ push إلى GitHub
  ☐ توثيق التغييرات
CHECKLIST

cat /tmp/refactoring-checklist.txt
```

### اليوم 2: التوثيق والتخطيط

#### 1️⃣ توثيق القيم الحالية

```bash
# توثيق جميع الـ hardcoded values:
cat > /tmp/hardcoded-values-list.txt << 'VALUES'
CURRENT HARDCODED VALUES
==========================

PATHS:
------
/opt/ai-company/infrastructure/.env
  • tools-api/server.py (2 مرات)
  • crew-service/crew.py (1 مرة)
  • secrets-sync/setup-infisical.py
  • secrets-sync/setup-portainer.py
  • secrets-sync/setup-openwebui.py
  • secrets-sync/write-env.py
  • secrets-sync/update-env.py
  • secrets-sync/get_secret.py

/opt/ai-company/data/openhands-state
  • secrets-sync/infisical-sync.sh (1 مرة)

/opt/ai-company/data/openhands
  • secrets-sync/generate-openhands-config.py (1 مرة)

/opt/workspace
  • secrets-sync/generate-openhands-config.py (1 مرة)

URLS/LOCALHOST:
---------------
http://localhost:8080 (Infisical)
  • secrets-sync/sync.py
  • secrets-sync/setup-infisical.py

http://localhost:8888 (Open WebUI)
  • secrets-sync/setup-openwebui.py

http://localhost:3000 (OpenHands)
  • secrets-sync/infisical-sync.sh

http://localhost:9443 (Portainer)
  • secrets-sync/setup-portainer.py

http://ai-tools-api:9000
  • tools-api/openwebui_tools.py

http://ai-openhands:3000
  • tools-api/server.py
  • crew-service/crew.py

http://ai-crew:9002
  • tools-api/server.py

http://ai-litellm:4000
  • crew-service/crew.py

ORGANIZATION NAMES:
-------------------
"AI Company" (Organization)
  • secrets-sync/setup-infisical.py

"ai-company" (Workspace)
  • secrets-sync/setup-infisical.py

API ENDPOINTS:
--------------
https://api.anthropic.com/v1/models
https://api.openai.com/v1/models
https://openrouter.ai/api/v1/models
https://api.github.com/user
https://api.github.com/user/repos
  • tools-api/server.py
VALUES

cat /tmp/hardcoded-values-list.txt
```

#### 2️⃣ إنشاء خريطة التعديلات

```bash
# خريطة تفصيلية لكل ملف:
cat > /tmp/modification-map.txt << 'MAP'
FILE MODIFICATION MAP
======================

FILE: .env.example (NEW)
────────────────────────
ACTION: Create new file with environment variables
CONTENT: All hardcoded values converted to variables
EXAMPLE:
  INSTALL_DIR=/opt/ai-company
  ORG_NAME=AI Company
  WORKSPACE_NAME=ai-company
  OPENHANDS_URL=http://ai-openhands:3000
  ... etc

FILE: install.sh
─────────────────
LINE: 1
CHANGE: Add INSTALL_DIR variable at the top
BEFORE: (none)
AFTER: INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"

CHANGE: Replace all /opt/ai-company with $INSTALL_DIR
BEFORE: TARGET="/opt/ai-company"
AFTER: TARGET="${INSTALL_DIR:-/opt/ai-company}"

FILE: bootstrap.sh
──────────────────
LINE: (all /opt/ai-company)
CHANGE: Replace all paths with $INSTALL_DIR
BEFORE: /opt/ai-company/infrastructure
AFTER: ${INSTALL_DIR:-/opt/ai-company}/infrastructure

FILE: docker-compose.yml
────────────────────────
CHANGE: Add environment variables section
BEFORE: services:
AFTER: 
  environment:
    - INSTALL_DIR=${INSTALL_DIR:-/opt/ai-company}
    - OPENHANDS_URL=${OPENHANDS_URL:-http://ai-openhands:3000}
    ... etc

FILE: tools-api/server.py
──────────────────────────
LINE: ~5
CHANGE: Convert hardcoded paths to variables
BEFORE: ENV_FILE = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")
AFTER:  INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
        ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

LINE: ~15-25
CHANGE: Add all URL variables
BEFORE: OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
AFTER: (keep as is, already using environ.get)

FILE: crew-service/crew.py
────────────────────────────
LINE: ~20
CHANGE: Same as server.py
BEFORE: env_file = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")
AFTER: INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
       ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

... and so on
MAP

cat /tmp/modification-map.txt
```

---

## 🟡 **المرحلة 2: التعديلات (اليوم 3-6)**

### اليوم 3: الملفات الأساسية

#### ملف 1: .env.example (NEW FILE)

```bash
# الملف الجديد:
cat > /home/claude/repo/.env.example << 'ENV'
# ========================================
# AI Company - Environment Configuration
# ========================================

# Installation Directory
INSTALL_DIR=/opt/ai-company

# Organization Configuration
ORG_NAME=AI Company
WORKSPACE_NAME=ai-company

# API URLs - Docker Network (Production)
OPENHANDS_URL=http://ai-openhands:3000
CREW_URL=http://ai-crew:9002
LITELLM_URL=http://ai-litellm:4000
INFISICAL_URL=http://ai-infisical:8080
OPENWEBUI_URL=http://ai-open-webui:8888
PORTAINER_URL=https://ai-portainer:9443
TOOLS_API_URL=http://ai-tools-api:9000

# API URLs - Localhost (Development)
# Uncomment these for local development:
# OPENHANDS_URL=http://localhost:3000
# CREW_URL=http://localhost:9002
# LITELLM_URL=http://localhost:4000
# INFISICAL_URL=http://localhost:8080
# OPENWEBUI_URL=http://localhost:8888
# PORTAINER_URL=https://localhost:9443
# TOOLS_API_URL=http://localhost:9000

# Data Directories
OPENHANDS_STATE_DIR=${INSTALL_DIR}/data/openhands-state
OPENHANDS_WORKSPACE=${INSTALL_DIR}/data/workspace

# Host Configuration
HOST_IP=localhost

# LLM Configuration
LITELLM_BASE_URL=${LITELLM_URL:-http://ai-litellm:4000}

# Secrets Configuration
SECRETS_SYNC_ENABLED=true
ENV

echo "✅ Created .env.example"
```

#### ملف 2: install.sh

```bash
# تعديل install.sh:
# سأعطيك الأسطر المحددة للتغيير

cat > /tmp/install_changes.txt << 'CHANGES'
FILE: install.sh
CHANGES:
=========

1. بعد السطر الأول (#!/bin/bash):
   ADD:
   # Installation directory configuration
   INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
   export INSTALL_DIR

2. استبدل جميع:
   FROM: TARGET="/opt/ai-company"
   TO:   TARGET="${INSTALL_DIR}"

3. استبدل جميع:
   FROM: /opt/ai-company
   TO:   ${INSTALL_DIR}

4. في الـ docker-compose line:
   FROM: docker compose -f /opt/ai-company/infrastructure/docker-compose.yml
   TO:   docker compose -f ${INSTALL_DIR}/infrastructure/docker-compose.yml

5. في الـ bootstrap call:
   ADD EXPORT:
   export INSTALL_DIR="${INSTALL_DIR}"
   before: ./bootstrap.sh
CHANGES

cat /tmp/install_changes.txt
```

#### ملف 3: bootstrap.sh

```bash
# تعديل bootstrap.sh:
cat > /tmp/bootstrap_changes.txt << 'CHANGES'
FILE: bootstrap.sh
CHANGES:
=========

1. بعد السطر الأول:
   ADD:
   INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
   export INSTALL_DIR

2. استبدل جميع /opt/ai-company:
   FROM: /opt/ai-company/infrastructure/.env
   TO:   ${INSTALL_DIR}/infrastructure/.env

3. في docker-compose commands:
   FROM: /opt/ai-company/infrastructure/docker-compose.yml
   TO:   ${INSTALL_DIR}/infrastructure/docker-compose.yml

4. في volume mounts:
   FROM: -v /opt/ai-company/data/openhands:/workspace
   TO:   -v ${INSTALL_DIR}/data/openhands:/workspace
CHANGES

cat /tmp/bootstrap_changes.txt
```

### اليوم 4: Docker Configuration

#### ملف 4: docker-compose.yml

```bash
# تعديل docker-compose.yml:
cat > /tmp/docker_compose_changes.txt << 'CHANGES'
FILE: infrastructure/docker-compose.yml
CHANGES:
=========

1. في قسم services، أضيف environment لكل service:

   BEFORE:
   services:
     ai-tools-api:
       image: ...
       ports: ...

   AFTER:
   services:
     ai-tools-api:
       image: ...
       ports: ...
       environment:
         - INSTALL_DIR=${INSTALL_DIR:-/opt/ai-company}
         - OPENHANDS_URL=${OPENHANDS_URL:-http://ai-openhands:3000}
         - CREW_URL=${CREW_URL:-http://ai-crew:9002}
         - LITELLM_URL=${LITELLM_URL:-http://ai-litellm:4000}
         - INFISICAL_URL=${INFISICAL_URL:-http://ai-infisical:8080}
         - HOST_IP=${HOST_IP:-localhost}

2. في volumes section:
   استبدل جميع:
   FROM: - /opt/ai-company/data/openhands:/workspace
   TO:   - ${INSTALL_DIR:-/opt/ai-company}/data/openhands:/workspace

3. في env_file:
   FROM: env_file: .env
   TO:   env_file: ${INSTALL_DIR:-/opt/ai-company}/infrastructure/.env
CHANGES

cat /tmp/docker_compose_changes.txt
```

### اليوم 5: Tools API

#### ملف 5: tools-api/server.py

```python
# Specific changes for server.py:
cat > /tmp/server_py_changes.txt << 'CHANGES'
FILE: tools-api/server.py
CHANGES:
=========

LINE: ~5-10 (at the top with other imports)
CHANGE: Add INSTALL_DIR variable
ADD:
    import os.path
    
    INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
    ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

BEFORE:
    ENV_FILE = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")

AFTER:
    ENV_FILE = os.environ.get("ENV_FILE_PATH", 
                             os.path.join(INSTALL_DIR, "infrastructure", ".env"))

LINE: ~40-50 (OPENHANDS_URL definitions)
ALREADY CORRECT:
    OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
    CREW_URL = os.environ.get("CREW_URL", "http://ai-crew:9002")
(NO CHANGE NEEDED)

LINE: ~200+ (في الـ function حيث يستدعي scripts)
CHANGE: Replace hardcoded paths
BEFORE:
    f"python3 {os.path.dirname(ENV_FILE).replace('infrastructure','secrets-sync')}/setup-openwebui.py"

AFTER:
    setup_script = os.path.join(INSTALL_DIR, "secrets-sync", "setup-openwebui.py")
    f"python3 {setup_script}"

LINE: socket.create_connection check
CHANGE: Add localhost fallback
NO CHANGE (already using "localhost" as default)
CHANGES

cat /tmp/server_py_changes.txt
```

### اليوم 6: Crew Service & Secrets Sync

#### ملف 6: crew-service/crew.py

```python
cat > /tmp/crew_py_changes.txt << 'CHANGES'
FILE: crew-service/crew.py
CHANGES:
=========

LINE: ~5 (at the top)
ADD:
    import os.path
    
    INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
    ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

BEFORE:
    env_file = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")

AFTER:
    env_file = ENV_FILE  # use the variable defined above

LINE: ~URL definitions
ALREADY CORRECT:
    OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://ai-openhands:3000")
    LITELLM_URL = os.environ.get("LITELLM_BASE_URL", "http://ai-litellm:4000")
(NO CHANGE NEEDED)
CHANGES

cat /tmp/crew_py_changes.txt
```

#### الملفات في secrets-sync/

```bash
cat > /tmp/secrets_sync_changes.txt << 'CHANGES'
FILE: secrets-sync/sync.py
CHANGE:
BEFORE: API = os.environ.get("INFISICAL_API_URL", "http://localhost:8080")
AFTER:  API = os.environ.get("INFISICAL_API_URL", 
                             os.environ.get("INFISICAL_URL", "http://ai-infisical:8080"))

FILE: secrets-sync/setup-infisical.py
CHANGES:
LINE: ~10
BEFORE: ENV_FILE = "/opt/ai-company/infrastructure/.env"
AFTER:  INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
        ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

LINE: ~20
BEFORE: BASE = os.environ.get("INFISICAL_API_URL", "http://localhost:8080")
AFTER:  BASE = os.environ.get("INFISICAL_API_URL", 
                              os.environ.get("INFISICAL_URL", "http://ai-infisical:8080"))

FILE: secrets-sync/setup-openwebui.py
SIMILAR CHANGES as setup-infisical.py

FILE: secrets-sync/setup-portainer.py
SIMILAR CHANGES as setup-infisical.py

FILE: secrets-sync/generate-openhands-config.py
CHANGES:
LINE: ~10
BEFORE: STATE_DIR = os.environ.get("OPENHANDS_STATE_DIR", "/opt/ai-company/data/openhands")
AFTER:  INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
        STATE_DIR = os.environ.get("OPENHANDS_STATE_DIR", 
                                   os.path.join(INSTALL_DIR, "data", "openhands"))

LINE: workspace_base
BEFORE: workspace_base = "/opt/workspace"
AFTER:  workspace_base = os.path.join(INSTALL_DIR, "data", "workspace")

FILE: secrets-sync/infisical-sync.sh
CHANGES:
LINE: ~5
ADD: INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
     export INSTALL_DIR

REPLACE ALL:
FROM: /opt/ai-company
TO:   ${INSTALL_DIR}

FILE: secrets-sync/write-env.py
FILE: secrets-sync/update-env.py
FILE: secrets-sync/get_secret.py
SIMILAR CHANGES to setup-infisical.py
CHANGES

cat /tmp/secrets_sync_changes.txt
```

---

## 🟢 **المرحلة 3: الاختبار والـ Deployment (اليوم 7-9)**

### اليوم 7: اختبار التعديلات

#### 1️⃣ تحضير بيئة اختبار نظيفة

```bash
# إنشاء بيئة اختبار:
mkdir -p /tmp/ai-company-test
cd /tmp/ai-company-test

# نسخ المستودع
git clone /home/claude/repo .

# الانتقال للـ branch الجديد:
git checkout refactor/remove-hardcoded-v1.7.1
```

#### 2️⃣ اختبار المتغيرات

```bash
# تجربة التثبيت مع متغيرات مختلفة:

# Test 1: القيم الافتراضية
unset INSTALL_DIR
./install.sh
# يجب يثبت في /opt/ai-company

# Test 2: مسار مخصص
export INSTALL_DIR="/custom/path/ai-company"
./install.sh
# يجب يثبت في /custom/path/ai-company

# Test 3: التحقق من البيئة
grep INSTALL_DIR /opt/ai-company/infrastructure/.env
# يجب تطبع القيمة الصحيحة
```

#### 3️⃣ التحقق من الملفات

```bash
# قائمة التحقق:
✓ .env.example موجود
✓ جميع الـ paths استخدم INSTALL_DIR
✓ جميع الـ URLs استخدم environment variables
✓ docker-compose.yml يحتوي environment الجديد
✓ Python files استخدم os.path.join
```

### اليوم 8: اختبار المنظومة

#### 1️⃣ اختبار Docker Services

```bash
# تشغيل المنظومة:
docker-compose -f ${INSTALL_DIR}/infrastructure/docker-compose.yml up -d

# التحقق من الـ services:
docker ps -a
# يجب تكون جميع services running

# التحقق من الـ volumes:
docker volume ls
# يجب يكون volumes للبيانات موجود
```

#### 2️⃣ اختبار الـ API

```bash
# اختبار Tools API:
curl http://localhost:9000/health
# يجب تكون response 200

# اختبار OpenHands:
curl http://localhost:3000/
# يجب تكون response

# التحقق من الـ .env loading:
curl http://localhost:9000/env | grep INSTALL_DIR
# يجب يطبع INSTALL_DIR
```

#### 3️⃣ اختبار الـ Secrets

```bash
# التحقق من تحميل الـ secrets:
docker exec ai-infisical curl http://localhost:8080/api/status
# يجب successful response

# التحقق من الـ .env:
cat ${INSTALL_DIR}/infrastructure/.env | head -20
# يجب يحتوي على جميع الـ variables
```

### اليوم 9: Commit والـ Deployment

#### 1️⃣ الـ Commit

```bash
# مراجعة نهائية:
cd /home/claude/repo
git diff refactor/remove-hardcoded-v1.7.1..main | wc -l
# يجب أكثر من 100 سطر

# عرض الملفات المعدلة:
git diff --name-only refactor/remove-hardcoded-v1.7.1..main

# Commit النهائي:
git add .
git commit -m "refactor: Remove hardcoded values and use environment variables

BREAKING CHANGE: INSTALL_DIR must be set in environment or .env

Changes:
- Convert /opt/ai-company hardcoded paths to INSTALL_DIR variable
- Convert localhost URLs to environment variables (INFISICAL_URL, OPENHANDS_URL, etc)
- Update docker-compose.yml to pass environment variables
- Update all Python scripts to use os.path.join for paths
- Create .env.example with all configuration options

Affected files:
- .env.example (new)
- install.sh
- bootstrap.sh
- docker-compose.yml
- tools-api/server.py
- tools-api/openwebui_tools.py
- crew-service/crew.py
- secrets-sync/*.py (8 files)
- infisical-sync.sh

Testing:
- ✓ Tested with default INSTALL_DIR
- ✓ Tested with custom INSTALL_DIR
- ✓ All services running
- ✓ All API endpoints working
- ✓ Secrets loading correctly

Fixes: #hardcoded-values
"
```

#### 2️⃣ الـ Push

```bash
# Push للـ branch:
git push origin refactor/remove-hardcoded-v1.7.1

# إنشاء Pull Request على GitHub:
# من refactor/remove-hardcoded-v1.7.1 إلى main
# مع رسالة تفصيلية
```

#### 3️⃣ Merge والـ Tag

```bash
# بعد المراجعة والـ approval:

# Merge:
git checkout main
git merge refactor/remove-hardcoded-v1.7.1

# Tag:
git tag -a v1.7.1 -m "Remove hardcoded values - use environment variables"

# Push:
git push origin main --tags
```

---

## ✅ **Post-Deployment Checklist**

```bash
☐ جميع الـ tests passing
☐ البيانات محفوظة
☐ Services تعمل
☐ Documentation محدثة
☐ CHANGELOG محدثة
☐ .env.example موجود
☐ README محدثة

# في production:
☐ Backup من البيانات القديمة موجود
☐ الـ Rollback procedure موثق
☐ Monitoring يعمل
☐ Logs محفوظة
```

---

## 🚨 **في حالة المشاكل: Rollback**

```bash
# إذا حصلت مشاكل في أي مرحلة:

# العودة للـ backup:
git checkout backup-v1.7.0-before-refactor

# أو:
git reset --hard HEAD~1

# استعادة البيانات:
cp /tmp/refactor-backup/.env.backup /opt/ai-company/infrastructure/.env

# إعادة تشغيل:
docker-compose down
docker-compose up -d
```

---

## 📊 **ملخص التغييرات**

```
المجموع:
  • 13 ملف تم تعديلها
  • 1 ملف جديد (.env.example)
  • ~150 سطر تم تعديلها
  • 45+ hardcoded values تم إزالتها

الفوائد:
  ✓ مرونة أعلى
  ✓ سهولة التثبيت في أماكن مختلفة
  ✓ سهولة التطوير (localhost)
  ✓ سهولة الـ production deployment
```

---

**الحالة:** ✅ جاهز للبدء  
**المخاطر:** منخفضة (مع اتباع الخطة)  
**الدعم:** موثق كاملاً

