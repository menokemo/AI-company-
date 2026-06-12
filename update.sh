#!/usr/bin/env bash
#
# سكربت التحديث — يجلب أحدث ملفات المنظومة من GitHub
# بديل عن git pull لأن التوكن في URL يسبب أخطاء ترميز.
# الاستخدام:  sudo bash /opt/ai-company/update.sh
#
set -euo pipefail

INSTALL_DIR="/opt/ai-company"
REPO="menokemo/AI-company-"
BRANCH="main"
API="https://api.github.com/repos/${REPO}/contents"

log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }

[ "$(id -u)" -eq 0 ] || { err "شغّله بصلاحية root:  sudo bash update.sh"; exit 1; }

read -rsp "GitHub Token: " GH_TOKEN; echo
[ -n "$GH_TOKEN" ] || { err "لم يُدخَل توكن."; exit 1; }

fetch_file() {
    local path="$1"
    local dest="$INSTALL_DIR/$path"
    mkdir -p "$(dirname "$dest")"
    local http_code
    http_code=$(curl -sf \
        -H "Authorization: Bearer $GH_TOKEN" \
        -H "Accept: application/vnd.github.raw+json" \
        -w "%{http_code}" \
        "https://raw.githubusercontent.com/${REPO}/${BRANCH}/${path}" \
        -o "$dest")
    [ "$http_code" = "200" ] || { err "فشل تحميل: $path (HTTP $http_code)"; return 1; }
    log "تم تحديث: $path"
}

# الملفات المُدارة (لا تشمل .env لحماية الأسرار)
FILES=(
    "infrastructure/docker-compose.yml"
    "llm-gateway/config.yaml"
    "secrets-sync/sync.py"
    "secrets-sync/infisical-sync.sh"
    "install.sh"
    "bootstrap.sh"
    "update.sh"
)

log "تحديث ملفات المنظومة من GitHub..."
for f in "${FILES[@]}"; do
    fetch_file "$f"
done

chmod +x "$INSTALL_DIR/install.sh" \
         "$INSTALL_DIR/bootstrap.sh" \
         "$INSTALL_DIR/update.sh" \
         "$INSTALL_DIR/secrets-sync/infisical-sync.sh" \
         "$INSTALL_DIR/secrets-sync/sync.py"

unset GH_TOKEN
log "اكتمل التحديث. لتطبيق التغييرات على الخدمات الجديدة شغّل:"
echo "  sudo docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml \\"
echo "    --env-file $INSTALL_DIR/infrastructure/.env up -d"
