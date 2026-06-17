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

# لو مفيش credentials — فشل فوراً (بدون أي تفاعل/انتظار input)
if [ -z "${INFISICAL_CLIENT_ID:-}" ] || [ -z "${INFISICAL_CLIENT_SECRET:-}" ] || [ -z "${INFISICAL_PROJECT_ID:-}" ]; then
    err "بيانات اتصال Infisical غير مكتملة — أدخلها في لوحة التحكم → Infisical Setup"
    exit 1
fi
INFISICAL_API_URL="${INFISICAL_API_URL:-http://localhost:8080}"
INFISICAL_ENV="${INFISICAL_ENV:-dev}"

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
# ملاحظة: لا نعيد تشغيل tools-api هنا لأن هذا الـ script غالباً يُستدعى
# من داخل tools-api نفسه عبر /system/sync — إعادة تشغيله سيقطع الـ HTTP response
# ملاحظة: docker restart لا يُعيد قراءة env_file — لازم --force-recreate
# عشان الـ secrets الجديدة تتحقن فعلياً في الـ container environment
log "إعادة تشغيل الخدمات بالمفاتيح الجديدة..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d --force-recreate litellm crew-service 2>/dev/null || true
if [ ! -f "/.dockerenv" ]; then
    # فقط لو الـ script شغّال على الـ host مباشرةً (مش من داخل container)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
        up -d --force-recreate tools-api 2>/dev/null || true
fi

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
