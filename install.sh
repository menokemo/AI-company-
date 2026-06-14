#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Company — Automated Install Script
# Usage: sudo bash install.sh --github-token ghp_xxxx [options]
# Options:
#   --github-token      GitHub token (required - for private repo access)
#   --infisical-id      Infisical Machine Identity Client ID
#   --infisical-secret  Infisical Machine Identity Client Secret
#   --infisical-project Infisical Project ID
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[→]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

ROOT_DIR=/opt/ai-company
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
ENV_FILE="$ROOT_DIR/infrastructure/.env"

GITHUB_TOKEN=""
INFISICAL_ID=""
INFISICAL_SECRET=""
INFISICAL_PROJ=""

# ── Parse arguments ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --github-token)      GITHUB_TOKEN="$2";    shift 2 ;;
        --infisical-id)      INFISICAL_ID="$2";    shift 2 ;;
        --infisical-secret)  INFISICAL_SECRET="$2"; shift 2 ;;
        --infisical-project) INFISICAL_PROJ="$2";  shift 2 ;;
        *) err "Unknown option: $1" ;;
    esac
done

[ -z "$GITHUB_TOKEN" ] && err "Required: --github-token ghp_xxxx"

gen_secret() { openssl rand -hex 32; }
gen_pass()   { openssl rand -base64 24 | tr -d '/+=' | head -c 20; }

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║       AI Company — Auto Installer        ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Prerequisites ──────────────────────────────────────────────────────
info "Checking prerequisites..."
command -v docker  >/dev/null 2>&1 || err "Docker is not installed"
command -v git     >/dev/null 2>&1 || err "Git is not installed"
command -v python3 >/dev/null 2>&1 || err "Python3 is not installed"
command -v openssl >/dev/null 2>&1 || err "OpenSSL is not installed"
docker compose version >/dev/null 2>&1 || err "Docker Compose V2 is not installed"
log "All prerequisites found"

# ── 2. Detect VM IP ───────────────────────────────────────────────────────
HOST_IP=$(hostname -I | awk '{print $1}')
log "VM IP: $HOST_IP"

# ── 3. Clone / Update repository ─────────────────────────────────────────
info "Cloning / updating repository..."
REPO_AUTH_URL="https://${GITHUB_TOKEN}@github.com/menokemo/AI-company-.git"

if [ -d "$ROOT_DIR/.git" ]; then
    git -C "$ROOT_DIR" remote set-url origin "$REPO_AUTH_URL"
    [ -f "$ENV_FILE" ] && cp "$ENV_FILE" /tmp/ai-company-env.bak
    git -C "$ROOT_DIR" fetch origin
    git -C "$ROOT_DIR" reset --hard origin/main
    git -C "$ROOT_DIR" clean -fd \
        --exclude=infrastructure/.env \
        --exclude=config/models.json \
        --exclude=data \
        --exclude=config/mockups
    [ -f /tmp/ai-company-env.bak ] && cp /tmp/ai-company-env.bak "$ENV_FILE"
    log "Repository updated"
else
    git clone "$REPO_AUTH_URL" "$ROOT_DIR"
    log "Repository cloned"
fi

# ── 4. Read existing .env values (preserve on reinstall) ─────────────────
info "Preparing secrets..."

get_env() {
    local key="$1" default="$2" val=""
    [ -f "$ENV_FILE" ] && val=$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    [ -n "$val" ] && echo "$val" || echo "$default"
}

LITELLM_MASTER_KEY=$(get_env "LITELLM_MASTER_KEY" "sk-$(gen_secret)")
WEBUI_SECRET_KEY=$(get_env "WEBUI_SECRET_KEY" "$(gen_secret)")
POSTGRES_USER=$(get_env "POSTGRES_USER" "infisical")
POSTGRES_PASSWORD=$(get_env "POSTGRES_PASSWORD" "$(gen_pass)")
POSTGRES_DB=$(get_env "POSTGRES_DB" "infisicaldb")
ENCRYPTION_KEY=$(get_env "ENCRYPTION_KEY" "$(gen_secret)")
AUTH_SECRET=$(get_env "AUTH_SECRET" "$(gen_secret)")
JWT_SIGNUP_SECRET=$(get_env "JWT_SIGNUP_SECRET" "$(gen_secret)")
JWT_REFRESH_SECRET=$(get_env "JWT_REFRESH_SECRET" "$(gen_secret)")
JWT_AUTH_SECRET=$(get_env "JWT_AUTH_SECRET" "$(gen_secret)")
JWT_SERVICE_SECRET=$(get_env "JWT_SERVICE_SECRET" "$(gen_secret)")
GIT_USERNAME=$(get_env "GIT_USERNAME" "")

# Infisical Machine Identity — from args or existing .env
INFISICAL_CLIENT_ID="${INFISICAL_ID:-$(get_env "INFISICAL_CLIENT_ID" "")}"
INFISICAL_CLIENT_SECRET="${INFISICAL_SECRET:-$(get_env "INFISICAL_CLIENT_SECRET" "")}"
INFISICAL_PROJECT_ID="${INFISICAL_PROJ:-$(get_env "INFISICAL_PROJECT_ID" "")}"

# External API keys — preserved from existing .env (populated via Infisical sync)
ANTHROPIC_API_KEY=$(get_env "ANTHROPIC_API_KEY" "")
OPENAI_API_KEY=$(get_env "OPENAI_API_KEY" "")
OPENROUTER_API_KEY=$(get_env "OPENROUTER_API_KEY" "")
AGENT_SERVER_IMAGE_TAG=$(get_env "AGENT_SERVER_IMAGE_TAG" "1.25.0-python")

log "Secrets prepared"

# ── 5. Write .env (using Python to avoid encoding issues) ─────────────────
info "Writing .env..."
mkdir -p "$ROOT_DIR/infrastructure"

python3 - << PYEOF
import os
lines = [
    "# AI Company - Environment Variables",
    "# Last updated: $(date '+%Y-%m-%d %H:%M')",
    "",
    "HOST_IP=${HOST_IP}",
    "",
    "# LiteLLM",
    "LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}",
    "",
    "# Open WebUI",
    "WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}",
    "OPEN_WEBUI_IMAGE_TAG=main",
    "",
    "# Infisical Database",
    "POSTGRES_USER=${POSTGRES_USER}",
    "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
    "POSTGRES_DB=${POSTGRES_DB}",
    "DB_CONNECTION_URI=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@ai-infisical-db:5432/${POSTGRES_DB}",
    "",
    "# Infisical App Secrets",
    "ENCRYPTION_KEY=${ENCRYPTION_KEY}",
    "AUTH_SECRET=${AUTH_SECRET}",
    "JWT_SIGNUP_SECRET=${JWT_SIGNUP_SECRET}",
    "JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}",
    "JWT_AUTH_SECRET=${JWT_AUTH_SECRET}",
    "JWT_SERVICE_SECRET=${JWT_SERVICE_SECRET}",
    "REDIS_URL=redis://ai-infisical-redis:6379",
    "",
    "# Infisical Machine Identity (for secrets sync)",
    "INFISICAL_CLIENT_ID=${INFISICAL_CLIENT_ID}",
    "INFISICAL_CLIENT_SECRET=${INFISICAL_CLIENT_SECRET}",
    "INFISICAL_PROJECT_ID=${INFISICAL_PROJECT_ID}",
    "",
    "# GitHub",
    "GITHUB_TOKEN=${GITHUB_TOKEN}",
    "GIT_USERNAME=${GIT_USERNAME}",
    "",
    "# External API Keys (added via Infisical sync)",
    "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}",
    "OPENAI_API_KEY=${OPENAI_API_KEY}",
    "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}",
    "",
    "# OpenHands",
    "AGENT_SERVER_IMAGE_TAG=${AGENT_SERVER_IMAGE_TAG}",
]
with open("${ENV_FILE}", "w") as f:
    f.write("\n".join(lines) + "\n")
print("  .env written successfully")
PYEOF
log ".env created / updated"

# ── 6. Create required directories ────────────────────────────────────────
info "Creating directories..."
mkdir -p "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace" "$ROOT_DIR/config/mockups"
[ ! -f "$ROOT_DIR/config/models.json" ] && echo '{}' > "$ROOT_DIR/config/models.json"
chown -R 1000:1000 "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace"
log "Directories ready"

# ── 7. OpenHands config ───────────────────────────────────────────────────
info "Configuring OpenHands..."
python3 "$ROOT_DIR/secrets-sync/generate-openhands-config.py" 2>/dev/null || true

# ── 8. Pull agent-server image ────────────────────────────────────────────
info "Pulling OpenHands agent-server image..."
docker pull ghcr.io/openhands/agent-server:${AGENT_SERVER_IMAGE_TAG} 2>/dev/null \
    || warn "Failed to pull agent-server image"

# ── 9. Start all services ─────────────────────────────────────────────────
info "Starting all services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
log "All services started"

# ── 10. Wait for Infisical ────────────────────────────────────────────────
info "Waiting for Infisical..."
for i in $(seq 1 30); do
    curl -sf "http://localhost:8080/api/v1/healthcheck" >/dev/null 2>&1 && break
    sleep 5
done
log "Infisical ready"

# ── 11. Auto-setup Infisical + sync ──────────────────────────────────────
info "Auto-configuring Infisical..."
python3 "$ROOT_DIR/secrets-sync/setup-infisical.py"     && log "Infisical configured automatically"     || warn "Auto-config failed — manual setup needed at http://localhost:8080"

# Re-read credentials (might have been created by setup-infisical.py)
INFISICAL_CLIENT_ID=$(grep "^INFISICAL_CLIENT_ID=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")
INFISICAL_CLIENT_SECRET=$(grep "^INFISICAL_CLIENT_SECRET=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")

# Use provided args if auto-setup didn't get credentials
[ -z "$INFISICAL_CLIENT_ID" ]     && INFISICAL_CLIENT_ID="$INFISICAL_ID"
[ -z "$INFISICAL_CLIENT_SECRET" ] && INFISICAL_CLIENT_SECRET="$INFISICAL_SECRET"

if [ -n "$INFISICAL_CLIENT_ID" ] && [ -n "$INFISICAL_CLIENT_SECRET" ]; then
    python3 "$ROOT_DIR/secrets-sync/update-env.py" \
        "INFISICAL_CLIENT_ID=$INFISICAL_CLIENT_ID" \
        "INFISICAL_CLIENT_SECRET=$INFISICAL_CLIENT_SECRET" \
        "INFISICAL_PROJECT_ID=$INFISICAL_PROJECT_ID" \
        "ENV_FILE=$ENV_FILE"
    info "Running Infisical sync..."
    bash "$ROOT_DIR/secrets-sync/infisical-sync.sh"         && log "Infisical sync completed — API keys loaded"         || warn "Infisical sync failed — run: sudo bash $ROOT_DIR/secrets-sync/infisical-sync.sh"
else
    warn "No Infisical credentials yet — open http://$(hostname -I | awk '{print $1}'):8080 to configure"
fi

# ── 12. Link GitHub to OpenHands ─────────────────────────────────────────
info "Linking GitHub to OpenHands..."
GH_LINKED=false
for attempt in 1 2 3 4 5; do
    sleep 15
    if curl -sf -X POST "http://localhost:3000/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\":{\"github\":{\"token\":\"$GITHUB_TOKEN\",\"user_id\":\"$GIT_USERNAME\",\"host\":\"github.com\"}}}" \
        >/dev/null 2>&1; then
        log "GitHub connected to OpenHands (attempt $attempt)"
        GH_LINKED=true
        break
    fi
done
[ "$GH_LINKED" = false ] && warn "GitHub link failed — run sync after setting GIT_USERNAME in Infisical"

# ── 13. Summary ───────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅ Installation Complete!                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🏠 Dashboard:      ${BLUE}http://$HOST_IP${NC}"
echo -e "  💬 Open WebUI:     ${BLUE}http://$HOST_IP:8888${NC}"
echo -e "  🤖 OpenHands:      ${BLUE}http://$HOST_IP:3000${NC}"
echo -e "  🔑 Infisical:      ${BLUE}http://$HOST_IP:8080${NC}"
echo -e "  🔀 LiteLLM:        ${BLUE}http://$HOST_IP:4000${NC}"
echo -e "  👥 Crew Pipeline:  ${BLUE}http://$HOST_IP:9002${NC}"
echo ""
echo -e "${YELLOW}Generated Secrets (keep safe):${NC}"
echo -e "  LITELLM_MASTER_KEY: ${CYAN}${LITELLM_MASTER_KEY:0:20}...${NC}"
echo -e "  WEBUI_SECRET_KEY:   ${CYAN}${WEBUI_SECRET_KEY:0:20}...${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Open Infisical (${BLUE}http://$HOST_IP:8080${NC}) and add API keys:"
echo -e "     - ANTHROPIC_API_KEY"
echo -e "     - OPENAI_API_KEY    (optional)"
echo -e "     - OPENROUTER_API_KEY (optional)"
echo -e "     - GIT_USERNAME"
echo ""
echo -e "  2. Run sync:  ${CYAN}sudo bash $ROOT_DIR/secrets-sync/infisical-sync.sh${NC}"
echo ""
echo -e "  3. Open OpenHands (${BLUE}http://$HOST_IP:3000${NC}) → Settings → LLM:"
echo -e "     Model: openai/claude | Base URL: http://$HOST_IP:4000"
echo ""
echo -e "  4. Open Dashboard (${BLUE}http://$HOST_IP${NC}) → select model for each agent"
echo ""
