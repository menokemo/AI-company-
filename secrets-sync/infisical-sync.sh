#!/usr/bin/env bash
#
# يسحب المفاتيح من Infisical ويحقنها في .env ثم يعيد تشغيل الخدمات
# الاستخدام: sudo bash secrets-sync/infisical-sync.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infrastructure"
ENV_FILE="$INFRA_DIR/.env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

# تحقق من الـ root (إلا لو داخل container)
[ "$(id -u)" -eq 0 ] || [ -f "/.dockerenv" ] || {
    err "شغّله بصلاحية root: sudo bash secrets-sync/infisical-sync.sh"
    exit 1
}

[ -f "$ENV_FILE" ] || { err ".env غير موجود — شغّل install.sh أولاً."; exit 1; }

command -v python3 >/dev/null 2>&1 || { apt-get update -y && apt-get install -y python3; }

# حمّل المتغيرات من .env
set -a; . "$ENV_FILE"; set +a

# إعداد تفاعلي لو مفيش credentials
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
        echo "INFISICAL_API_URL=$INFISICAL_API_URL"
        echo "INFISICAL_CLIENT_ID=$INFISICAL_CLIENT_ID"
        echo "INFISICAL_CLIENT_SECRET=$INFISICAL_CLIENT_SECRET"
        echo "INFISICAL_PROJECT_ID=$INFISICAL_PROJECT_ID"
        echo "INFISICAL_ENV=$INFISICAL_ENV"
    } >> "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    log "تم حفظ بيانات الاتصال."
fi

# ── سحب المفاتيح من Infisical ────────────────────────────────────────────────
log "سحب المفاتيح من Infisical..."
INFISICAL_API_URL="${INFISICAL_API_URL:-http://localhost:8080}" \
INFISICAL_CLIENT_ID="$INFISICAL_CLIENT_ID" \
INFISICAL_CLIENT_SECRET="$INFISICAL_CLIENT_SECRET" \
INFISICAL_PROJECT_ID="$INFISICAL_PROJECT_ID" \
INFISICAL_ENV="${INFISICAL_ENV:-dev}" \
ENV_FILE="$ENV_FILE" \
MANAGED_KEYS="ANTHROPIC_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY GITHUB_TOKEN" \
python3 "$SCRIPT_DIR/sync.py"

# ── توليد إعدادات OpenHands ──────────────────────────────────────────────────
log "توليد إعدادات OpenHands..."
OPENHANDS_STATE_DIR="/opt/ai-company/data/openhands-state" \
ENV_FILE="$ENV_FILE" \
python3 "$SCRIPT_DIR/generate-openhands-config.py"

# ── إعادة تشغيل الخدمات ──────────────────────────────────────────────────────
log "إعادة تشغيل الخدمات..."
docker restart ai-litellm ai-tools-api ai-crew 2>/dev/null || true

# ── ربط GitHub بـ OpenHands ──────────────────────────────────────────────────
GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")
GIT_USERNAME=$(grep "^GIT_USERNAME=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")

if [ -n "$GITHUB_TOKEN" ] && [ -n "$GIT_USERNAME" ]; then
    log "ربط GitHub بـ OpenHands..."
    sleep 5
    resp=$(curl -sf -X POST "http://localhost:3000/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\":{\"github\":{\"token\":\"$GITHUB_TOKEN\",\"user_id\":\"$GIT_USERNAME\",\"host\":\"github.com\"}}}" \
        2>/dev/null || echo "")
    echo "$resp" | grep -q "stored" && log "✓ GitHub متصل بـ OpenHands" || true
fi

log "✅ تم الـ sync بنجاح!"
exit 0
