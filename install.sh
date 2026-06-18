#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Company — Install Script
# Usage: sudo bash install.sh --github-token ghp_xxxx
# Optional: --infisical-id ID --infisical-secret SECRET --infisical-project ID
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[→]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# Installation directory configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
export INSTALL_DIR

ROOT_DIR="${INSTALL_DIR}"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
ENV_FILE="$ROOT_DIR/infrastructure/.env"

GITHUB_TOKEN=""
INFISICAL_ID=""
INFISICAL_SECRET=""
INFISICAL_PROJ=""

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
gen_pass()   { openssl rand -base64 18 | tr -d '/+=' | head -c 20; }

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║       AI Company — Auto Installer v2         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Prerequisites ──────────────────────────────────────────────────────
info "Checking prerequisites..."
command -v docker  >/dev/null 2>&1 || err "Docker not installed"
command -v git     >/dev/null 2>&1 || err "Git not installed"
command -v python3 >/dev/null 2>&1 || err "Python3 not installed"
command -v openssl >/dev/null 2>&1 || err "OpenSSL not installed"
docker compose version >/dev/null 2>&1 || err "Docker Compose V2 not installed"
log "Prerequisites OK"

# ── 1.5. Configure Docker permissions ─────────────────────────────────────
info "Configuring Docker permissions..."
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "root" ]; then
    if ! groups "$CURRENT_USER" | grep -q docker; then
        warn "Adding $CURRENT_USER to docker group..."
        usermod -aG docker "$CURRENT_USER"
        newgrp docker <<EOF
echo "Docker permissions updated for $CURRENT_USER"
EOF
    fi
fi
log "Docker permissions OK"

# ── 2. Detect VM IP ───────────────────────────────────────────────────────
HOST_IP=$(hostname -I | awk '{print $1}')
log "VM IP: $HOST_IP"

# ── 3. Clone / Update repository ─────────────────────────────────────────
info "Cloning / updating repository..."

if [ -d "$ROOT_DIR/.git" ]; then
    # Repository already exists, just update it
    log "Repository found, updating..."
    git -C "$ROOT_DIR" remote set-url origin "https://github.com/menokemo/AI-company-.git"
    [ -f "$ENV_FILE" ] && cp "$ENV_FILE" /tmp/ai-company-env.bak
    
    # Use git credential helper to handle token safely
    export GIT_TERMINAL_PROMPT=0
    GIT_AUTHOR_NAME="ai-company" GIT_AUTHOR_EMAIL="dev@ai-company.local" \
    git -C "$ROOT_DIR" -c "credential.helper=store" fetch origin 2>/dev/null || true
    
    git -C "$ROOT_DIR" reset --hard origin/main
    git -C "$ROOT_DIR" clean -fd \
        --exclude=infrastructure/.env \
        --exclude=config/models.json \
        --exclude=data \
        --exclude=config/mockups
    [ -f /tmp/ai-company-env.bak ] && cp /tmp/ai-company-env.bak "$ENV_FILE"
    log "Repository updated"
else
    # Clone new repository with token
    log "Cloning repository..."
    
    # Use helper script to clone safely
    if ! git clone "https://${GITHUB_TOKEN}@github.com/menokemo/AI-company-.git" "$ROOT_DIR" 2>/dev/null; then
        # If token auth fails, try without token (public repo)
        warn "Token auth failed, trying public clone..."
        git clone "https://github.com/menokemo/AI-company-.git" "$ROOT_DIR"
    fi
    
    # Secure git config
    git -C "$ROOT_DIR" remote set-url origin "https://github.com/menokemo/AI-company-.git"
fi

log "Repository ready"

# ── 4. Generate / preserve secrets ───────────────────────────────────────
info "Preparing secrets..."

get_env() {
    local key="$1" default="$2" val=""
    [ -f "$ENV_FILE" ] && val=$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    [ -n "$val" ] && echo "$val" || echo "$default"
}

# Internal secrets — generate once, preserve on reinstall
LITELLM_MASTER_KEY=$(get_env "LITELLM_MASTER_KEY" "sk-$(gen_secret)")
WEBUI_SECRET_KEY=$(get_env "WEBUI_SECRET_KEY" "$(gen_secret)")
POSTGRES_USER=$(get_env "POSTGRES_USER" "infisical")
POSTGRES_PASSWORD=$(get_env "POSTGRES_PASSWORD" "$(gen_pass)")
POSTGRES_DB=$(get_env "POSTGRES_DB" "infisicaldb")
ENCRYPTION_KEY=$(get_env "ENCRYPTION_KEY" "$(openssl rand -hex 16)")
AUTH_SECRET=$(get_env "AUTH_SECRET" "$(openssl rand -base64 32 | tr -d "\n")")
JWT_SIGNUP_SECRET=$(get_env "JWT_SIGNUP_SECRET" "$(gen_secret)")
JWT_REFRESH_SECRET=$(get_env "JWT_REFRESH_SECRET" "$(gen_secret)")
JWT_AUTH_SECRET=$(get_env "JWT_AUTH_SECRET" "$(gen_secret)")
JWT_SERVICE_SECRET=$(get_env "JWT_SERVICE_SECRET" "$(gen_secret)")

# Service admin accounts — generated once
INFISICAL_ADMIN_EMAIL=$(get_env "INFISICAL_ADMIN_EMAIL" "admin@ai-company.local")
INFISICAL_ADMIN_PASSWORD=$(get_env "INFISICAL_ADMIN_PASSWORD" "$(gen_pass)")
WEBUI_ADMIN_EMAIL=$(get_env "WEBUI_ADMIN_EMAIL" "admin@ai-company.local")
WEBUI_ADMIN_PASSWORD=$(get_env "WEBUI_ADMIN_PASSWORD" "$(gen_pass)")
PORTAINER_ADMIN_USER=$(get_env "PORTAINER_ADMIN_USER" "admin")
PORTAINER_ADMIN_PASSWORD=$(get_env "PORTAINER_ADMIN_PASSWORD" "$(gen_pass)")

# Infisical Machine Identity — from args or existing .env
INFISICAL_CLIENT_ID="${INFISICAL_ID:-$(get_env "INFISICAL_CLIENT_ID" "")}"
INFISICAL_CLIENT_SECRET="${INFISICAL_SECRET:-$(get_env "INFISICAL_CLIENT_SECRET" "")}"
INFISICAL_PROJECT_ID="${INFISICAL_PROJ:-$(get_env "INFISICAL_PROJECT_ID" "")}"

# External API keys — preserved from previous sync
GITHUB_TOKEN_STORED=$(get_env "GITHUB_TOKEN" "$GITHUB_TOKEN")
GIT_USERNAME=$(get_env "GIT_USERNAME" "")
# Auto-detect GIT_USERNAME from GITHUB_TOKEN if not set
if [ -z "$GIT_USERNAME" ] && [ -n "$GITHUB_TOKEN_STORED" ]; then
    GIT_USERNAME=$(curl -sf -H "Authorization: Bearer $GITHUB_TOKEN_STORED"         https://api.github.com/user 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('login',''))" 2>/dev/null || echo "")
fi
ANTHROPIC_API_KEY=$(get_env "ANTHROPIC_API_KEY" "")
OPENAI_API_KEY=$(get_env "OPENAI_API_KEY" "")
OPENROUTER_API_KEY=$(get_env "OPENROUTER_API_KEY" "")
AGENT_SERVER_IMAGE_TAG=$(get_env "AGENT_SERVER_IMAGE_TAG" "1.25.0-python")

log "Secrets prepared"

# ── 5. Write .env (Python to avoid encoding issues) ──────────────────────
info "Writing .env..."
mkdir -p "$ROOT_DIR/infrastructure"

python3 "$ROOT_DIR/secrets-sync/write-env.py" \
    "ENV_FILE=$ENV_FILE" \
    "HOST_IP=$HOST_IP" \
    "LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY" \
    "WEBUI_SECRET_KEY=$WEBUI_SECRET_KEY" \
    "OPEN_WEBUI_IMAGE_TAG=main" \
    "POSTGRES_USER=$POSTGRES_USER" \
    "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" \
    "POSTGRES_DB=$POSTGRES_DB" \
    "DB_CONNECTION_URI=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@ai-infisical-db:5432/$POSTGRES_DB" \
    "ENCRYPTION_KEY=$ENCRYPTION_KEY" \
    "AUTH_SECRET=$AUTH_SECRET" \
    "JWT_SIGNUP_SECRET=$JWT_SIGNUP_SECRET" \
    "JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET" \
    "JWT_AUTH_SECRET=$JWT_AUTH_SECRET" \
    "JWT_SERVICE_SECRET=$JWT_SERVICE_SECRET" \
    "REDIS_URL=redis://ai-infisical-redis:6379" \
    "INFISICAL_ADMIN_EMAIL=$INFISICAL_ADMIN_EMAIL" \
    "INFISICAL_ADMIN_PASSWORD=$INFISICAL_ADMIN_PASSWORD" \
    "INFISICAL_CLIENT_ID=$INFISICAL_CLIENT_ID" \
    "INFISICAL_CLIENT_SECRET=$INFISICAL_CLIENT_SECRET" \
    "INFISICAL_PROJECT_ID=$INFISICAL_PROJECT_ID" \
    "WEBUI_ADMIN_EMAIL=$WEBUI_ADMIN_EMAIL" \
    "WEBUI_ADMIN_PASSWORD=$WEBUI_ADMIN_PASSWORD" \
    "PORTAINER_ADMIN_USER=$PORTAINER_ADMIN_USER" \
    "PORTAINER_ADMIN_PASSWORD=$PORTAINER_ADMIN_PASSWORD" \
    "GIT_USERNAME=$GIT_USERNAME" \
    "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
    "OPENAI_API_KEY=$OPENAI_API_KEY" \
    "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" \
    "AGENT_SERVER_IMAGE_TAG=$AGENT_SERVER_IMAGE_TAG"

log ".env written"

# ── 6. Create directories ─────────────────────────────────────────────────
info "Creating directories..."
mkdir -p "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace" "$ROOT_DIR/config/mockups"
[ ! -f "$ROOT_DIR/config/models.json" ] && echo '{}' > "$ROOT_DIR/config/models.json"
chown -R 1000:1000 "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace" 2>/dev/null || true
log "Directories ready"

# ── 7. OpenHands config ───────────────────────────────────────────────────
info "Configuring OpenHands..."
python3 "$ROOT_DIR/secrets-sync/generate-openhands-config.py" 2>/dev/null || true

# ── 8. Pull agent-server image ────────────────────────────────────────────
info "Pulling OpenHands agent-server ($AGENT_SERVER_IMAGE_TAG)..."
docker pull ghcr.io/openhands/agent-server:${AGENT_SERVER_IMAGE_TAG} 2>/dev/null \
    || warn "Could not pull agent-server image"

# ── 9. Start all services ─────────────────────────────────────────────────
info "Starting all services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
log "All services started"

# ── 10-12. All setup in background (waits for Infisical) ─────────────────
cat > /tmp/ai-company-post-install.sh << 'BGSCRIPT'
#!/bin/bash
LOG=/var/log/ai-company-setup.log

echo "[setup] Waiting for Infisical to be healthy..."
for i in $(seq 1 150); do
    sleep 5
    HEALTH=$(docker inspect ai-infisical --format='{{.State.Health.Status}}' 2>/dev/null || echo '')
    [ "$HEALTH" = "healthy" ] && { echo "[setup] ✓ Infisical healthy (${i}x5s)"; break; }
    curl -sf http://localhost:8080/api/status 2>/dev/null | grep -q '"message":"Ok"' && { echo "[setup] ✓ Infisical API ready (${i}x5s)"; break; }
    [ $((i % 12)) -eq 0 ] && echo "[setup] Still waiting (${i}x5s) [$HEALTH]"
done

BGSCRIPT

# إضافة المتغيرات في الـ script
cat >> /tmp/ai-company-post-install.sh << BGVARS
ROOT_DIR="$ROOT_DIR"
COMPOSE_FILE="$COMPOSE_FILE"
ENV_FILE="$ENV_FILE"
HOST_IP="$HOST_IP"
INFISICAL_ID="$INFISICAL_ID"
INFISICAL_SECRET="$INFISICAL_SECRET"
INFISICAL_PROJ="$INFISICAL_PROJ"
BGVARS

cat >> /tmp/ai-company-post-install.sh << 'BGSCRIPT2'
echo "[setup] Setting up Infisical..."
python3 "$ROOT_DIR/secrets-sync/setup-infisical.py"     && echo "[setup] ✓ Infisical configured"     || echo "[setup] ! Infisical setup — use Dashboard to configure"

if [ -n "$INFISICAL_ID" ]; then
    python3 "$ROOT_DIR/secrets-sync/update-env.py"         "INFISICAL_CLIENT_ID=$INFISICAL_ID"         "INFISICAL_CLIENT_SECRET=$INFISICAL_SECRET"         "INFISICAL_PROJECT_ID=$INFISICAL_PROJ"         "ENV_FILE=$ENV_FILE"
fi

CID=$(grep "^INFISICAL_CLIENT_ID=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ -n "$CID" ]; then
    echo "[setup] Syncing from Infisical..."
    bash "$ROOT_DIR/secrets-sync/infisical-sync.sh"         && echo "[setup] ✓ Sync done" || echo "[setup] ! Sync failed"
fi

echo "[setup] Setting up Open WebUI..."
python3 "$ROOT_DIR/secrets-sync/setup-openwebui.py"     && echo "[setup] ✓ Open WebUI ready" || echo "[setup] ! Open WebUI failed"

echo "[setup] Setting up Portainer..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE"     up -d --force-recreate portainer 2>/dev/null
sleep 15
python3 "$ROOT_DIR/secrets-sync/setup-portainer.py"     && echo "[setup] ✓ Portainer ready" || echo "[setup] ! Portainer — configure via https://$HOST_IP:9443"

echo "[setup] ✅ All post-install setup complete!"
BGSCRIPT2

chmod +x /tmp/ai-company-post-install.sh
nohup bash /tmp/ai-company-post-install.sh >> /var/log/ai-company-setup.log 2>&1 &
log "Post-install running in background"
log "Monitor: tail -f /var/log/ai-company-setup.log"


# ── 15. Summary ───────────────────────────────────────────────────────────
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
echo -e "  🐳 Portainer:      ${BLUE}https://$HOST_IP:9443${NC}"
echo ""
echo -e "${YELLOW}All credentials available in Dashboard → 🔐 Access Credentials${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Open Infisical (${BLUE}http://$HOST_IP:8080${NC})"
echo -e "     Add your API keys: ANTHROPIC_API_KEY, OPENAI_API_KEY, GITHUB_TOKEN etc."
echo ""
echo -e "  2. Click ${CYAN}🔄 Sync from Infisical${NC} in the Dashboard"
echo ""
echo -e "  3. Open Dashboard → select model for each Crew agent"
echo ""
