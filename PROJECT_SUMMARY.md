# AI Company — Project Summary

## الوصف
منظومة شركة برمجة بالذكاء الاصطناعي — تحوّل أفكار العملاء لتطبيقات حقيقية بشكل شبه أوتوماتيك.

## البنية التحتية

| الخدمة | البورت | الوظيفة |
|--------|--------|---------|
| Dashboard | 80 | لوحة التحكم الرئيسية |
| Open WebUI | 8888 | واجهة الدردشة + مدير المشروع |
| OpenHands | 3000 | AI Coding Agent |
| Infisical | 8080 | إدارة الـ secrets |
| LiteLLM | 4000 | Proxy للـ LLM APIs |
| Crew Pipeline | 9002 | Pipeline الـ 6 agents |
| Tools API | 9000 | API داخلي |
| Portainer | 9443 | إدارة Docker |

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
كلها في: لوحة التحكم → Access Credentials → Show

## الـ Post-Install Steps
1. Infisical → Sign Up → Machine Identity
2. لوحة التحكم → Infisical Setup → Save & Sync
3. Infisical → أضف: ANTHROPIC_API_KEY, GITHUB_TOKEN, GIT_USERNAME
4. لوحة التحكم → Sync Now
5. لوحة التحكم → موديلات المنظومة → اختار موديل لكل agent → Save

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
| `secrets-sync/setup-*.py` | إعداد الخدمات |

## الميزات
- **سجل أعمال الموظفين** (تبويب في لوحة التحكم): يعرض كل تشغيلة سابقة — ماذا أنتج كل agent + نتيجة OpenHands، محفوظ على القرص. الـ API: `GET /run-history` (tools-api).
- **إعادة محاولة تلقائية**: لـ race condition معروف في OpenHands SDK (sandbox startup)، ولـ rate-limit الموديلات المجانية في OpenRouter.

## مُخطَّط له (لم يُنفَّذ بعد)
- **إعادة تصميم لوحة التحكم**: تحويلها من صفحة واحدة طويلة لـ sidebar + تبويبات (نظرة عامة، إعداد Infisical، الموديلات، سجل الأعمال، بيانات الدخول)، مع دعم كامل للموبايل (responsive). الخطة المتفق عليها: 4 مراحل — (١) تخطيط التبويبات [تم الاتفاق]، (٢) بناء الهيكل على الديسكتوب، (٣) دعم الموبايل، (٤) تلميع نهائي. **لم نبدأ التنفيذ بعد.**

## الـ PENDING
- [x] اختبار Pipeline كامل من Open WebUI لـ OpenHands — تم التأكد فعليًا (commit حقيقي + كود مكتوب) في 2026-06-17
- [x] إنشاء مدير المشروع أوتوماتيك بعد اختيار الموديل — مُنفّذ في `setup-openwebui.py`
- [ ] PR creation من OpenHands
