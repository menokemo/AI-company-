#!/usr/bin/env bash
set -euo pipefail

# ── ألوان ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

ROOT_DIR=/opt/ai-company
REPO_URL="https://github.com/menokemo/AI-company-"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
ENV_FILE="$ROOT_DIR/infrastructure/.env"

# ── اكتشاف IP الـ VM ─────────────────────────────────────────────────────
HOST_IP=$(hostname -I | awk '{print $1}')
log "VM IP: $HOST_IP"

# ── المتطلبات ─────────────────────────────────────────────────────────────
log "التحقق من المتطلبات..."
command -v docker  >/dev/null 2>&1 || err "Docker غير مثبّت"
command -v git     >/dev/null 2>&1 || err "Git غير مثبّت"
docker compose version >/dev/null 2>&1 || err "Docker Compose V2 غير مثبّت"

# ── استنساخ/تحديث الريبو ─────────────────────────────────────────────────
if [ -d "$ROOT_DIR/.git" ]; then
    log "تحديث الريبو..."
    git -C "$ROOT_DIR" pull --ff-only
else
    log "استنساخ الريبو..."
    git clone "$REPO_URL" "$ROOT_DIR"
fi

# ── إنشاء المجلدات اللازمة ────────────────────────────────────────────────
log "إنشاء المجلدات..."
mkdir -p "$ROOT_DIR/data/openhands"
mkdir -p "$ROOT_DIR/data/workspace"
mkdir -p "$ROOT_DIR/config/mockups"
chown -R 1000:1000 "$ROOT_DIR/data/openhands"
chown -R 1000:1000 "$ROOT_DIR/data/workspace"

# ── إنشاء models.json فارغ إذا لم يوجد ──────────────────────────────────
if [ ! -f "$ROOT_DIR/config/models.json" ]; then
    echo '{}' > "$ROOT_DIR/config/models.json"
    log "models.json جديد — اختر الموديلات من لوحة التحكم بعد التثبيت"
fi

# ── إضافة HOST_IP لـ .env ─────────────────────────────────────────────────
if ! grep -q "^HOST_IP=" "$ENV_FILE" 2>/dev/null; then
    echo "HOST_IP=$HOST_IP" >> "$ENV_FILE"
    log "HOST_IP=$HOST_IP أُضيف لـ .env"
else
    sed -i "s/^HOST_IP=.*/HOST_IP=$HOST_IP/" "$ENV_FILE"
fi

# ── تحميل agent-server مسبقاً ────────────────────────────────────────────
log "تحميل OpenHands agent-server (قد يأخذ بعض الوقت)..."
docker pull ghcr.io/openhands/agent-server:1.25.0-python || warn "فشل تحميل agent-server"

# ── config.toml لـ OpenHands ──────────────────────────────────────────────
python3 "$ROOT_DIR/secrets-sync/generate-openhands-config.py"

# ── تشغيل كل الخدمات ─────────────────────────────────────────────────────
log "تشغيل الخدمات..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

# ── انتظار جاهزية الخدمات ────────────────────────────────────────────────
log "انتظار جاهزية الخدمات..."
sleep 30

# ── ربط GitHub بـ OpenHands ──────────────────────────────────────────────
GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$ENV_FILE" | cut -d= -f2-)
GIT_USERNAME=$(grep "^GIT_USERNAME=" "$ENV_FILE" | cut -d= -f2-)
if [ -n "$GITHUB_TOKEN" ] && [ -n "$GIT_USERNAME" ]; then
    log "ربط GitHub بـ OpenHands..."
    curl -sf -X POST "http://localhost:3000/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\": {\"github\": {\"token\": \"$GITHUB_TOKEN\", \"user_id\": \"$GIT_USERNAME\", \"host\": \"github.com\"}}}" \
        >/dev/null 2>&1 && log "GitHub متصل بـ OpenHands" || warn "فشل ربط GitHub"
fi

# ── ملخص ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ التثبيت اكتمل!${NC}"
echo ""
echo -e "  🏠 لوحة التحكم:    ${BLUE}http://$HOST_IP${NC}"
echo -e "  💬 Open WebUI:     ${BLUE}http://$HOST_IP:8888${NC}"
echo -e "  🤖 OpenHands:      ${BLUE}http://$HOST_IP:3000${NC}"
echo -e "  🔑 Infisical:      ${BLUE}http://$HOST_IP:8080${NC}"
echo -e "  🔀 LiteLLM:        ${BLUE}http://$HOST_IP:4000${NC}"
echo -e "  👥 Crew Pipeline:  ${BLUE}http://$HOST_IP:9002${NC}"
echo ""
echo -e "${YELLOW}⚠️  خطوة مهمة بعد التثبيت:${NC}"
echo -e "   1. افتح OpenHands (:3000) → Settings → LLM"
echo -e "      Name: litellm | Model: openai/claude"
echo -e "      Base URL: http://$HOST_IP:4000 | API Key: من Infisical"
echo -e "   2. افتح لوحة التحكم (:80) → اختر موديل لكل موظف"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
