#!/usr/bin/env bash
#
# سكربت التحديث — أمر واحد بدون إدخال يدوي
# يقرأ GITHUB_TOKEN من Infisical تلقائياً
# الاستخدام:  sudo bash /opt/ai-company/update.sh
#
set -euo pipefail

INSTALL_DIR="/opt/ai-company"
ENV_FILE="$INSTALL_DIR/infrastructure/.env"
COMPOSE_FILE="$INSTALL_DIR/infrastructure/docker-compose.yml"
REPO="menokemo/AI-company-"
BRANCH="main"

log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

[ "$(id -u)" -eq 0 ] || { err "شغّله بـ: sudo bash $0"; exit 1; }
[ -f "$ENV_FILE" ]    || { err ".env غير موجود."; exit 1; }

set -a; . "$ENV_FILE"; set +a

log "جلب GITHUB_TOKEN من Infisical..."
GH_TOKEN=$(python3 "$INSTALL_DIR/secrets-sync/get_secret.py" GITHUB_TOKEN 2>/dev/null || true)
[ -n "$GH_TOKEN" ] || { err "GITHUB_TOKEN غير موجود في Infisical — أضفه من واجهة Infisical ثم أعد التشغيل."; exit 1; }

fetch() {
  local path="$1" dest="$INSTALL_DIR/$1" code
  mkdir -p "$(dirname "$dest")"
  code=$(curl -sf \
    -H "Authorization: Bearer $GH_TOKEN" \
    -H "Accept: application/vnd.github.raw+json" \
    -w "%{http_code}" \
    "https://raw.githubusercontent.com/${REPO}/${BRANCH}/${path}" \
    -o "$dest")
  [ "$code" = "200" ] && log "✓ $path" || { err "فشل: $path (HTTP $code)"; return 1; }
}

for f in "infrastructure/docker-compose.yml" "llm-gateway/config.yaml" \
         "secrets-sync/sync.py" "secrets-sync/get_secret.py" \
         "secrets-sync/infisical-sync.sh" "update.sh"; do
  fetch "$f"
done

chmod +x "$INSTALL_DIR/update.sh" \
         "$INSTALL_DIR/secrets-sync/sync.py" \
         "$INSTALL_DIR/secrets-sync/get_secret.py" \
         "$INSTALL_DIR/secrets-sync/infisical-sync.sh"

log "تطبيق التحديثات..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans
log "اكتمل التحديث."
