#!/usr/bin/env bash
#
# سكربت تثبيت منظومة AI Company
# يُشغَّل على الـ VM بصلاحية root:  sudo ./install.sh
# آمن لإعادة التشغيل (idempotent): لا يعيد توليد الأسرار إن كانت موجودة.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/infrastructure"
ENV_FILE="$INFRA_DIR/.env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

log()  { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[!]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

# 1) التحقق من صلاحية root
if [ "$(id -u)" -ne 0 ]; then
  err "شغّل السكربت بصلاحية root:  sudo ./install.sh"
  exit 1
fi

# 2) الأدوات المطلوبة
if ! command -v openssl >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
  log "تثبيت الأدوات المطلوبة (curl, openssl)..."
  apt-get update -y
  apt-get install -y curl openssl ca-certificates
fi

# 3) Docker
if ! command -v docker >/dev/null 2>&1; then
  log "تثبيت Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  log "Docker موجود بالفعل."
fi

if ! docker compose version >/dev/null 2>&1; then
  err "إضافة 'docker compose' غير متاحة. رجاءً حدّث Docker إلى إصدار يدعمها."
  exit 1
fi

# 4) الأسرار وملف البيئة
if [ -f "$ENV_FILE" ]; then
  log "ملف .env موجود — سيُحافَظ على الأسرار الحالية (لن يُعاد توليدها)."
else
  log "توليد الأسرار وإنشاء ملف .env..."
  IP="$(hostname -I | awk '{print $1}')"
  PG_PASS="$(openssl rand -hex 24)"
  cat > "$ENV_FILE" <<EOF
# صور Docker
INFISICAL_IMAGE_TAG=latest
LITELLM_IMAGE_TAG=main-stable
PORTAINER_IMAGE_TAG=lts
POSTGRES_IMAGE_TAG=14-alpine
REDIS_IMAGE_TAG=7-alpine
DIND_IMAGE_TAG=27-dind
OPENHANDS_IMAGE_TAG=0.38

# Postgres (Infisical)
POSTGRES_USER=infisical
POSTGRES_PASSWORD=$PG_PASS
POSTGRES_DB=infisical

# Infisical
ENCRYPTION_KEY=$(openssl rand -hex 16)
AUTH_SECRET=$(openssl rand -base64 32)
DB_CONNECTION_URI=postgres://infisical:$PG_PASS@infisical-db:5432/infisical
REDIS_URL=redis://infisical-redis:6379
SITE_URL=http://$IP:8080
OTEL_TELEMETRY_COLLECTION_ENABLED=false

# LiteLLM
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
EOF
  chmod 600 "$ENV_FILE"
  log "تم إنشاء .env وحمايته (600)."
fi

# 5) رفع الخدمات
log "تنزيل الصور..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
log "تجهيز مساحة عمل OpenHands..."
docker volume create ai-company_openhands_state 2>/dev/null || true
docker run --rm \
  -v ai-company_openhands_state:/.openhands-state \
  alpine chown -R 1000:1000 /.openhands-state

log "تشغيل الخدمات..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# 6) ملخّص الوصول
IP="$(hostname -I | awk '{print $1}')"
echo
log "اكتمل التثبيت. الواجهات المتاحة:"
echo "  • Portainer : https://$IP:9443"
echo "  • Infisical : http://$IP:8080"
echo "  • LiteLLM   : http://$IP:4000"
echo
warn "الخطوات التالية:"
echo "  1) افتح Infisical وأنشئ حساب المدير."
echo "  2) أضف مفاتيح الـ API (مثل ANTHROPIC_API_KEY) داخل Infisical."
echo "  3) سنربط LiteLLM والوكلاء بـ Infisical في الطبقة التالية."
