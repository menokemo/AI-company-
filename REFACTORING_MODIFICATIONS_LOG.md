# 📝 سجل التعديلات - Hardcoded Values Refactoring

**التاريخ:** 2026-06-18  
**الإصدار:** v1.7.0 → v1.7.1  
**Branch:** refactor/remove-hardcoded-v1.7.1

---

## 📊 خريطة التعديلات التفصيلية

### اليوم 3: الملفات الأساسية (install.sh, bootstrap.sh, .env.example)

#### ملف 1: .env.example (NEW FILE)
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الوصف:** إنشاء ملف قالب جديد بجميع environment variables

```
الموقع: /home/claude/repo/.env.example
المحتوى:
  • INSTALL_DIR=/opt/ai-company
  • ORG_NAME=AI Company
  • WORKSPACE_NAME=ai-company
  • OPENHANDS_URL=http://ai-openhands:3000
  • CREW_URL=http://ai-crew:9002
  • LITELLM_URL=http://ai-litellm:4000
  • INFISICAL_URL=http://ai-infisical:8080
  • OPENWEBUI_URL=http://ai-open-webui:8888
  • PORTAINER_URL=https://ai-portainer:9443
  • TOOLS_API_URL=http://ai-tools-api:9000
  • OPENHANDS_STATE_DIR=${INSTALL_DIR}/data/openhands-state
  • HOST_IP=localhost
```

---

#### ملف 2: install.sh
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الحجم:** 14K
**الأسطر المتأثرة:** ~15 سطر

**التعديلات:**
```bash
السطر 1: بعد #!/bin/bash
  ADD: INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
  ADD: export INSTALL_DIR

السطر 45 (تقريباً):
  FROM: TARGET="/opt/ai-company"
  TO:   TARGET="${INSTALL_DIR}"

جميع occurrences من /opt/ai-company:
  FROM: /opt/ai-company
  TO:   ${INSTALL_DIR}

في docker-compose line:
  FROM: docker compose -f /opt/ai-company/infrastructure/docker-compose.yml
  TO:   docker compose -f ${INSTALL_DIR}/infrastructure/docker-compose.yml
```

---

#### ملف 3: bootstrap.sh
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الحجم:** 1.6K
**الأسطر المتأثرة:** ~8 سطور

**التعديلات:**
```bash
السطر 1: بعد #!/bin/bash
  ADD: INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
  ADD: export INSTALL_DIR

جميع /opt/ai-company:
  FROM: /opt/ai-company
  TO:   ${INSTALL_DIR}
```

---

### اليوم 4: Docker Configuration (docker-compose.yml)

#### ملف 4: docker-compose.yml
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الحجم:** 6.4K
**الأسطر المتأثرة:** ~20 سطر

**التعديلات:**
```yaml
لكل service، أضيف environment:
  environment:
    - INSTALL_DIR=${INSTALL_DIR:-/opt/ai-company}
    - OPENHANDS_URL=${OPENHANDS_URL:-http://ai-openhands:3000}
    - CREW_URL=${CREW_URL:-http://ai-crew:9002}
    - LITELLM_URL=${LITELLM_URL:-http://ai-litellm:4000}
    - INFISICAL_URL=${INFISICAL_URL:-http://ai-infisical:8080}
    - HOST_IP=${HOST_IP:-localhost}

في volumes section:
  FROM: /opt/ai-company/data/openhands:/workspace
  TO:   ${INSTALL_DIR:-/opt/ai-company}/data/openhands:/workspace
```

---

### اليوم 5: Tools API (server.py, openwebui_tools.py)

#### ملف 5: tools-api/server.py
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الحجم:** متوسط
**الأسطر المتأثرة:** ~10 سطور

**التعديلات:**
```python
السطر ~5:
  ADD: import os.path
  ADD: INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
  ADD: ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")

السطر ~10:
  FROM: ENV_FILE = os.environ.get("ENV_FILE_PATH", "/opt/ai-company/infrastructure/.env")
  REMOVE: (استخدم الـ variable من فوق)
```

---

#### ملف 6: tools-api/openwebui_tools.py
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🟡 مهم
**الأسطر المتأثرة:** ~3 سطور

**التعديلات:**
```python
السطر ~5:
  ADD: INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
```

---

### اليوم 6: Crew Service & Secrets (crew.py, secrets-sync files)

#### ملف 7: crew-service/crew.py
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🔴 حرج
**الأسطر المتأثرة:** ~5 سطور

**التعديلات:**
```python
السطر ~5:
  ADD: INSTALL_DIR = os.environ.get("INSTALL_DIR", "/opt/ai-company")
  ADD: ENV_FILE = os.path.join(INSTALL_DIR, "infrastructure", ".env")
```

---

#### الملفات في secrets-sync/ (8 ملفات)
**الحالة:** ❌ لم يتم بعد
**الأولوية:** 🟡 مهم

```
sync.py - 1-2 تعديلات
setup-infisical.py - 2-3 تعديلات
setup-openwebui.py - 2-3 تعديلات
setup-portainer.py - 2-3 تعديلات
generate-openhands-config.py - 3-4 تعديلات
write-env.py - 1-2 تعديلات
update-env.py - 1-2 تعديلات
get_secret.py - 1-2 تعديلات
infisical-sync.sh - 5+ تعديلات
```

---

## 📋 Checklist

### اليوم 1: ✅ COMPLETED
- [x] git commit الحالة الحالية
- [x] إنشاء backup branch
- [x] إنشاء work branch
- [x] backup الملفات
- [x] توثيق القيم الحالية

### اليوم 2: 🟡 IN PROGRESS
- [x] مراجعة الملفات المتأثرة
- [ ] إنشاء خريطة التعديلات (هنا الآن)
- [ ] اختبار البيئة

### اليوم 3: ❌ TODO
- [ ] إنشاء .env.example
- [ ] تعديل install.sh
- [ ] تعديل bootstrap.sh

### اليوم 4: ❌ TODO
- [ ] تعديل docker-compose.yml
- [ ] اختبار أولي

### اليوم 5: ❌ TODO
- [ ] تعديل tools-api/server.py
- [ ] تعديل tools-api/openwebui_tools.py

### اليوم 6: ❌ TODO
- [ ] تعديل crew-service/crew.py
- [ ] تعديل جميع secrets-sync/*.py

### اليوم 7-9: ❌ TODO
- [ ] اختبار شامل
- [ ] commit و push
- [ ] merge و deploy

---

**آخر تحديث:** 2026-06-18  
**الحالة:** جاهز لـ اليوم 3 ✅

