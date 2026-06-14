#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Company — Install Script
# كل الـ secrets تتولّد أوتوماتيك. API keys الخارجية تُضاف من Infisical بعدين.
# استخدام: sudo bash install.sh --github-token ghp_xxxx
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[→]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── إعدادات ───────────────────────────────────────────────────────────────
ROOT_DIR=/opt/ai-company
REPO_URL="https://github.com/menokemo/AI-company-"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
ENV_FILE="$ROOT_DIR/infrastructure/.env"
GITHUB_TOKEN=""

# ── قراءة الـ arguments ───────────────────────────────────────────────────
INFISICAL_ID=""
INFISICAL_SECRET=""
INFISICAL_PROJ=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --github-token)      GITHUB_TOKEN="$2";    shift 2 ;;
        --infisical-id)      INFISICAL_ID="$2";    shift 2 ;;
        --infisical-secret)  INFISICAL_SECRET="$2"; shift 2 ;;
        --infisical-project) INFISICAL_PROJ="$2";  shift 2 ;;
        *) err "خيار غير معروف: $1" ;;
    esac
done

[ -z "$GITHUB_TOKEN" ] && err "مطلوب: --github-token ghp_xxxx"

# ── دالة توليد secret عشوائي ────────────────────────────────────────────
gen_secret() { openssl rand -hex 32; }
gen_pass()   { openssl rand -base64 24 | tr -d '/+=' | head -c 20; }

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║     AI Company — نظام التثبيت التلقائي  ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── ١. المتطلبات ──────────────────────────────────────────────────────────
info "التحقق من المتطلبات..."
command -v docker   >/dev/null 2>&1 || err "Docker غير مثبّت"
command -v git      >/dev/null 2>&1 || err "Git غير مثبّت"
command -v python3  >/dev/null 2>&1 || err "Python3 غير مثبّت"
command -v openssl  >/dev/null 2>&1 || err "OpenSSL غير مثبّت"
docker compose version >/dev/null 2>&1 || err "Docker Compose V2 غير مثبّت"
log "كل المتطلبات موجودة"

# ── ٢. IP الـ VM ─────────────────────────────────────────────────────────
HOST_IP=$(hostname -I | awk '{print $1}')
log "VM IP: $HOST_IP"

# ── ٣. استنساخ الريبو ────────────────────────────────────────────────────
info "استنساخ/تحديث الريبو..."
REPO_AUTH_URL="https://${GITHUB_TOKEN}@github.com/menokemo/AI-company-.git"

if [ -d "$ROOT_DIR/.git" ]; then
    git -C "$ROOT_DIR" remote set-url origin "$REPO_AUTH_URL"
    # احفظ .env قبل الـ reset (فيه secrets)
    [ -f "$ENV_FILE" ] && cp "$ENV_FILE" /tmp/ai-company-env.bak
    git -C "$ROOT_DIR" fetch origin
    git -C "$ROOT_DIR" reset --hard origin/main
    git -C "$ROOT_DIR" clean -fd --exclude=infrastructure/.env         --exclude=config/models.json --exclude=data --exclude=config/mockups
    # أرجع .env
    [ -f /tmp/ai-company-env.bak ] && cp /tmp/ai-company-env.bak "$ENV_FILE"
    log "الريبو محدّث"
else
    git clone "$REPO_AUTH_URL" "$ROOT_DIR"
    log "الريبو منسوخ"
fi

# ── ٤. توليد كل الـ secrets تلقائياً ───────────────────────────────────
info "توليد الـ secrets..."

# فحص: لو .env موجود، نحتفظ بالـ secrets الموجودة
if [ -f "$ENV_FILE" ]; then
    warn ".env موجود — سيتم الاحتفاظ بالـ secrets الحالية"
    source "$ENV_FILE" 2>/dev/null || true
fi

LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-$(gen_secret)}"
WEBUI_SECRET_KEY="${WEBUI_SECRET_KEY:-$(gen_secret)}"
POSTGRES_USER="${POSTGRES_USER:-infisical}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(gen_pass)}"
POSTGRES_DB="${POSTGRES_DB:-infisicaldb}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(gen_secret)}"
AUTH_SECRET="${AUTH_SECRET:-$(gen_secret)}"
JWT_SIGNUP_SECRET="${JWT_SIGNUP_SECRET:-$(gen_secret)}"
JWT_REFRESH_SECRET="${JWT_REFRESH_SECRET:-$(gen_secret)}"
JWT_AUTH_SECRET="${JWT_AUTH_SECRET:-$(gen_secret)}"
JWT_SERVICE_SECRET="${JWT_SERVICE_SECRET:-$(gen_secret)}"
INFISICAL_ADMIN_EMAIL="${INFISICAL_ADMIN_EMAIL:-admin@ai-company.local}"
INFISICAL_ADMIN_PASSWORD="${INFISICAL_ADMIN_PASSWORD:-$(gen_pass)}"

log "تم توليد كل الـ secrets"

# ── ٥. كتابة .env ─────────────────────────────────────────────────────────
info "إنشاء .env..."
mkdir -p "$ROOT_DIR/infrastructure"

cat > "$ENV_FILE" << EOF
# ══════════════════════════════════════════════════════════
# AI Company — Environment Variables
# مولَّد تلقائياً بتاريخ: $(date +%Y-%m-%d)
# ══════════════════════════════════════════════════════════

# ── معلومات الـ VM ────────────────────────────────────────
HOST_IP=$HOST_IP

# ── LiteLLM ───────────────────────────────────────────────
LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY

# ── Open WebUI ────────────────────────────────────────────
WEBUI_SECRET_KEY=$WEBUI_SECRET_KEY
OPEN_WEBUI_IMAGE_TAG=main

# ── Infisical Database ────────────────────────────────────
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
DB_CONNECTION_URI=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@ai-infisical-db:5432/$POSTGRES_DB

# ── Infisical Secrets ─────────────────────────────────────
ENCRYPTION_KEY=$ENCRYPTION_KEY
AUTH_SECRET=$AUTH_SECRET
JWT_SIGNUP_SECRET=$JWT_SIGNUP_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
JWT_AUTH_SECRET=$JWT_AUTH_SECRET
JWT_SERVICE_SECRET=$JWT_SERVICE_SECRET
REDIS_URL=redis://ai-infisical-redis:6379

# ── GitHub (مطلوب لعمل repos) ────────────────────────────
GITHUB_TOKEN=$GITHUB_TOKEN
GIT_USERNAME=

# ── API Keys الخارجية (تُضاف من Infisical بعد التثبيت) ──
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=

# ── OpenHands ─────────────────────────────────────────────
AGENT_SERVER_IMAGE_TAG=1.25.0-python
EOF

log ".env تم إنشاؤه"

# ── ٦. إنشاء المجلدات ────────────────────────────────────────────────────
info "إنشاء المجلدات..."
mkdir -p "$ROOT_DIR/data/openhands"
mkdir -p "$ROOT_DIR/data/workspace"
mkdir -p "$ROOT_DIR/config/mockups"
[ ! -f "$ROOT_DIR/config/models.json" ] && echo '{}' > "$ROOT_DIR/config/models.json"
chown -R 1000:1000 "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace"
log "المجلدات جاهزة"

# ── ٧. توليد config OpenHands ─────────────────────────────────────────────
info "إعداد OpenHands..."
python3 "$ROOT_DIR/secrets-sync/generate-openhands-config.py" 2>/dev/null || true

# ── ٨. تحميل agent-server مسبقاً ────────────────────────────────────────
info "تحميل OpenHands agent-server..."
docker pull ghcr.io/openhands/agent-server:1.25.0-python 2>/dev/null || warn "فشل تحميل agent-server"

# ── ٩. تشغيل الخدمات ─────────────────────────────────────────────────────
info "تشغيل كل الخدمات..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
log "كل الخدمات شغّالة"

# ── ١٠. انتظار Infisical ──────────────────────────────────────────────────
info "انتظار Infisical..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8080/api/v1/healthcheck" >/dev/null 2>&1; then
        log "Infisical جاهز"
        break
    fi
    sleep 5
done

# ── ١١. ربط GitHub بـ OpenHands ──────────────────────────────────────────
info "ربط GitHub بـ OpenHands (محاولات متعددة)..."
GH_LINKED=false
for attempt in 1 2 3 4 5; do
    sleep 15
    if curl -sf -X POST "http://localhost:3000/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\":{\"github\":{\"token\":\"$GITHUB_TOKEN\",\"user_id\":\"$GIT_USERNAME\",\"host\":\"github.com\"}}}" \
        >/dev/null 2>&1; then
        log "GitHub متصل بـ OpenHands (محاولة $attempt)"
        GH_LINKED=true
        break
    fi
    info "محاولة $attempt فشلت، إعادة المحاولة..."
done
[ "$GH_LINKED" = false ] && warn "فشل ربط GitHub — شغّل: sudo bash $ROOT_DIR/secrets-sync/infisical-sync.sh"

# ── ١٢. تشغيل Infisical sync تلقائياً لو credentials موجودة ──────────────
INFISICAL_CLIENT_ID=$(grep "^INFISICAL_CLIENT_ID=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ -n "$INFISICAL_CLIENT_ID" ]; then
    info "Infisical credentials موجودة — تشغيل sync تلقائي..."
    bash "$ROOT_DIR/secrets-sync/infisical-sync.sh" && log "Sync اكتمل — كل الـ secrets محدّثة" || warn "فشل Sync — شغّله يدوياً بعد إعداد Infisical"
else
    warn "لم يتم sync من Infisical — أضف credentials وشغّل sync يدوياً"
fi

# ── ١٢. ملخص التثبيت ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅ التثبيت اكتمل بنجاح!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🏠 لوحة التحكم:   ${BLUE}http://$HOST_IP${NC}"
echo -e "  💬 Open WebUI:    ${BLUE}http://$HOST_IP:8888${NC}"
echo -e "  🤖 OpenHands:     ${BLUE}http://$HOST_IP:3000${NC}"
echo -e "  🔑 Infisical:     ${BLUE}http://$HOST_IP:8080${NC}"
echo -e "  🔀 LiteLLM:       ${BLUE}http://$HOST_IP:4000${NC}"
echo -e "  👥 Crew Pipeline: ${BLUE}http://$HOST_IP:9002${NC}"
echo ""
echo -e "${YELLOW}══ الـ Secrets المولَّدة (احتفظ بها بأمان) ══${NC}"
echo -e "  LITELLM_MASTER_KEY:    ${CYAN}${LITELLM_MASTER_KEY:0:20}...${NC}"
echo -e "  WEBUI_SECRET_KEY:      ${CYAN}${WEBUI_SECRET_KEY:0:20}...${NC}"
echo -e "  INFISICAL_ADMIN:       ${CYAN}$INFISICAL_ADMIN_EMAIL${NC}"
echo ""
echo -e "${YELLOW}══ الخطوات التالية ══${NC}"
echo -e "  ١. افتح Infisical: ${BLUE}http://$HOST_IP:8080${NC}"
echo -e "     أنشئ حساب admin وأضف API keys:"
echo -e "     - ANTHROPIC_API_KEY"
echo -e "     - OPENAI_API_KEY    (اختياري)"
echo -e "     - OPENROUTER_API_KEY (اختياري)"
echo ""
echo -e "  ٢. شغّل sync:"
echo -e "     ${CYAN}sudo bash $ROOT_DIR/secrets-sync/infisical-sync.sh${NC}"
echo ""
echo -e "  ٣. افتح OpenHands (:3000) → Settings → LLM"
echo -e "     Model: openai/claude | Base URL: http://$HOST_IP:4000"
echo ""
echo -e "  ٤. اختر موديلات Crew من لوحة التحكم (:80)"
echo ""
