#!/usr/bin/env bash
#
# ربط Infisical بـ LiteLLM:
# يسحب المفاتيح من Infisical ويحقنها في .env ثم يعيد تشغيل LiteLLM.
# الاستخدام:  sudo bash secrets-sync/infisical-sync.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infrastructure"
ENV_FILE="$INFRA_DIR/.env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

[ "$(id -u)" -eq 0 ] || { err "شغّله بصلاحية root:  sudo bash secrets-sync/infisical-sync.sh"; exit 1; }
[ -f "$ENV_FILE" ] || { err ".env غير موجود — شغّل install.sh أولاً."; exit 1; }

command -v python3 >/dev/null 2>&1 || { apt-get update -y && apt-get install -y python3; }

# حمّل القيم الحالية للتحقق من وجود بيانات الاتصال
set -a; . "$ENV_FILE"; set +a

if [ -z "${INFISICAL_CLIENT_ID:-}" ]; then
  echo "— إعداد اتصال Infisical (مرة واحدة) —"
  read -rp "Infisical API URL [http://localhost:8080]: " API_IN
  INFISICAL_API_URL="${API_IN:-http://localhost:8080}"
  read -rp "Client ID: " INFISICAL_CLIENT_ID
  read -rsp "Client Secret (مخفي): " INFISICAL_CLIENT_SECRET; echo
  read -rp "Project ID: " INFISICAL_PROJECT_ID
  read -rp "Environment slug [dev]: " ENV_IN
  INFISICAL_ENV="${ENV_IN:-dev}"

  {
    echo ""
    echo "# اتصال Infisical (Machine Identity) — تُقرأ منها المفاتيح"
    echo "INFISICAL_API_URL=$INFISICAL_API_URL"
    echo "INFISICAL_CLIENT_ID=$INFISICAL_CLIENT_ID"
    echo "INFISICAL_CLIENT_SECRET=$INFISICAL_CLIENT_SECRET"
    echo "INFISICAL_PROJECT_ID=$INFISICAL_PROJECT_ID"
    echo "INFISICAL_ENV=$INFISICAL_ENV"
  } >> "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  log "تم حفظ بيانات الاتصال في .env (محميّ 600)."
fi

log "سحب المفاتيح من Infisical..."
INFISICAL_API_URL="${INFISICAL_API_URL:-http://localhost:8080}" \
INFISICAL_CLIENT_ID="$INFISICAL_CLIENT_ID" \
INFISICAL_CLIENT_SECRET="$INFISICAL_CLIENT_SECRET" \
INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
INFISICAL_ENV="${INFISICAL_ENV:-dev}" \
ENV_FILE="$ENV_FILE" \
MANAGED_KEYS="ANTHROPIC_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY GITHUB_TOKEN" \
python3 "$SCRIPT_DIR/sync.py"

log "توليد إعدادات OpenHands تلقائياً..."
OPENHANDS_STATE_DIR="/opt/ai-company/data/openhands-state" \
ENV_FILE="$ENV_FILE" \
python3 "$SCRIPT_DIR/generate-openhands-config.py"

log "إعادة تشغيل LiteLLM بالمفاتيح الجديدة..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d litellm

log "إعادة تشغيل tools-api بالمفاتيح الجديدة..."
docker compose -f "$ROOT_DIR/infrastructure/docker-compose.yml" \
  --env-file "$ENV_FILE" up -d tools-api

log "إعادة تشغيل OpenHands بالإعدادات الجديدة..."
docker compose -f "$ROOT_DIR/infrastructure/docker-compose.yml" \
  --env-file "$ENV_FILE" up -d openhands

# ─── ربط GitHub بـ OpenHands أوتوماتيك ─────────────────────────────────────
setup_openhands_github() {
    local token="$1" username="$2" oh_url="${3:-http://localhost:3000}"
    log "ربط GitHub بـ OpenHands..."
    local resp
    resp=$(curl -sf -X POST "$oh_url/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\": {\"github\": {\"token\": \"$token\", \"user_id\": \"$username\", \"host\": \"github.com\"}}}" \
        2>/dev/null)
    if echo "$resp" | grep -q "stored"; then
        log "✓ GitHub متصل بـ OpenHands"
    else
        warn "تحذير: ربط GitHub بـ OpenHands: $resp"
    fi
}

log "تم الربط. لإعادة المزامنة بعد أي تعديل في Infisical، شغّل نفس الأمر."

# ربط GitHub بـ OpenHands
gh_token=$(grep "^GITHUB_TOKEN=" "$ENV_FILE" | cut -d= -f2-)
gh_user=$(grep "^GIT_USERNAME=" "$ENV_FILE" | cut -d= -f2-)
if [ -n "$gh_token" ] && [ -n "$gh_user" ]; then
    sleep 5  # انتظار OpenHands يشتغل
    setup_openhands_github "$gh_token" "$gh_user"
fi
