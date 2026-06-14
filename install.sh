#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
info() { echo -e "${CYAN}[>>]${NC} $*"; }
warn() { echo -e "${YELLOW}[!!]${NC} $*"; }
err()  { echo -e "${RED}[XX]${NC} $*"; exit 1; }

ROOT_DIR=/opt/ai-company
REPO_URL="https://github.com/menokemo/AI-company-"
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
        *) err "unknown option: $1" ;;
    esac
done

[ -z "$GITHUB_TOKEN" ] && err "required: --github-token ghp_xxxx"

gen_secret() { openssl rand -hex 32; }
gen_pass()   { openssl rand -base64 24 | tr -d '/+=' | head -c 20; }

echo -e "${BLUE}"
echo "=========================================="
echo "   AI Company - Auto Install"
echo "=========================================="
echo -e "${NC}"

# 1. prerequisites
info "Checking prerequisites..."
command -v docker   >/dev/null 2>&1 || err "Docker not installed"
command -v git      >/dev/null 2>&1 || err "Git not installed"
command -v python3  >/dev/null 2>&1 || err "Python3 not installed"
command -v openssl  >/dev/null 2>&1 || err "OpenSSL not installed"
docker compose version >/dev/null 2>&1 || err "Docker Compose V2 not installed"
log "All prerequisites OK"

# 2. VM IP
HOST_IP=$(hostname -I | awk '{print $1}')
log "VM IP: $HOST_IP"

# 3. Clone/update repo
info "Cloning/updating repo..."
REPO_AUTH_URL="https://${GITHUB_TOKEN}@github.com/menokemo/AI-company-.git"
if [ -d "$ROOT_DIR/.git" ]; then
    git -C "$ROOT_DIR" remote set-url origin "$REPO_AUTH_URL"
    [ -f "$ENV_FILE" ] && cp "$ENV_FILE" /tmp/ai-env-backup.env
    git -C "$ROOT_DIR" fetch origin
    git -C "$ROOT_DIR" reset --hard origin/main
    git -C "$ROOT_DIR" clean -fd \
        --exclude=infrastructure/.env \
        --exclude=config/models.json \
        --exclude=data \
        --exclude=config/mockups
    [ -f /tmp/ai-env-backup.env ] && cp /tmp/ai-env-backup.env "$ENV_FILE"
    log "Repo updated"
else
    git clone "$REPO_AUTH_URL" "$ROOT_DIR"
    log "Repo cloned"
fi

# 4. Read existing .env values via Python (avoids bash encoding issues)
info "Preparing secrets..."
mkdir -p "$ROOT_DIR/infrastructure"

python3 - << PYEOF
import os, sys

env_file = "$ENV_FILE"
existing = {}
try:
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                existing[k.strip()] = v.strip()
except:
    pass

def get(key, default=''):
    v = existing.get(key, '') or default
    return v

import subprocess, datetime

def gen_secret():
    return subprocess.check_output(['openssl','rand','-hex','32']).decode().strip()

def gen_pass():
    r = subprocess.check_output(['openssl','rand','-base64','24']).decode().strip()
    return r.replace('/','').replace('+','').replace('=','')[:20]

# Use existing or generate new
vals = {}
vals['HOST_IP']                = os.environ.get('HOST_IP', get('HOST_IP'))
vals['LITELLM_MASTER_KEY']     = get('LITELLM_MASTER_KEY') or 'sk-' + gen_secret()
vals['WEBUI_SECRET_KEY']       = get('WEBUI_SECRET_KEY') or gen_secret()
vals['OPEN_WEBUI_IMAGE_TAG']   = get('OPEN_WEBUI_IMAGE_TAG', 'main')
vals['POSTGRES_USER']          = get('POSTGRES_USER', 'infisical')
vals['POSTGRES_PASSWORD']      = get('POSTGRES_PASSWORD') or gen_pass()
vals['POSTGRES_DB']            = get('POSTGRES_DB', 'infisical')
vals['ENCRYPTION_KEY']         = get('ENCRYPTION_KEY') or gen_secret()
vals['AUTH_SECRET']            = get('AUTH_SECRET') or gen_secret()
vals['JWT_SIGNUP_SECRET']      = get('JWT_SIGNUP_SECRET') or gen_secret()
vals['JWT_REFRESH_SECRET']     = get('JWT_REFRESH_SECRET') or gen_secret()
vals['JWT_AUTH_SECRET']        = get('JWT_AUTH_SECRET') or gen_secret()
vals['JWT_SERVICE_SECRET']     = get('JWT_SERVICE_SECRET') or gen_secret()
vals['REDIS_URL']              = 'redis://ai-infisical-redis:6379'
vals['DB_CONNECTION_URI']      = f"postgresql://{vals['POSTGRES_USER']}:{vals['POSTGRES_PASSWORD']}@ai-infisical-db:5432/{vals['POSTGRES_DB']}"

# Infisical machine credentials - from args OR existing .env
vals['INFISICAL_CLIENT_ID']     = os.environ.get('INFISICAL_ID','') or get('INFISICAL_CLIENT_ID','')
vals['INFISICAL_CLIENT_SECRET'] = os.environ.get('INFISICAL_SECRET','') or get('INFISICAL_CLIENT_SECRET','')
vals['INFISICAL_PROJECT_ID']    = os.environ.get('INFISICAL_PROJ','') or get('INFISICAL_PROJECT_ID','')

# GitHub
vals['GITHUB_TOKEN']  = os.environ.get('GITHUB_TOKEN','') or get('GITHUB_TOKEN','')
vals['GIT_USERNAME']  = get('GIT_USERNAME','')

# External API keys - preserve existing (from previous sync)
vals['ANTHROPIC_API_KEY']   = get('ANTHROPIC_API_KEY','')
vals['OPENAI_API_KEY']      = get('OPENAI_API_KEY','')
vals['OPENROUTER_API_KEY']  = get('OPENROUTER_API_KEY','')

# OpenHands
vals['AGENT_SERVER_IMAGE_TAG'] = get('AGENT_SERVER_IMAGE_TAG','1.25.0-python')

# Write .env
lines = [f"# AI Company .env - {datetime.date.today()}"]
for k, v in vals.items():
    lines.append(f"{k}={v}")
with open(env_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('env written OK')
PYEOF

log ".env created/updated"

# Pass Infisical credentials to Python via env
export INFISICAL_ID INFISICAL_SECRET INFISICAL_PROJ GITHUB_TOKEN HOST_IP

# 5. Create directories
info "Creating directories..."
mkdir -p "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace" "$ROOT_DIR/config/mockups"
[ ! -f "$ROOT_DIR/config/models.json" ] && echo '{}' > "$ROOT_DIR/config/models.json"
chown -R 1000:1000 "$ROOT_DIR/data/openhands" "$ROOT_DIR/data/workspace" 2>/dev/null || true
log "Directories ready"

# 6. OpenHands config
python3 "$ROOT_DIR/secrets-sync/generate-openhands-config.py" 2>/dev/null || true

# 7. Pull agent-server
info "Pulling OpenHands agent-server..."
AGENT_TAG=$(grep "^AGENT_SERVER_IMAGE_TAG=" "$ENV_FILE" | cut -d= -f2)
docker pull "ghcr.io/openhands/agent-server:${AGENT_TAG:-1.25.0-python}" 2>/dev/null || \
    warn "Failed to pull agent-server"

# 8. Start all services
info "Starting all services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
log "All services started"

# 9. Wait for Infisical
info "Waiting for Infisical..."
for i in $(seq 1 30); do
    curl -sf "http://localhost:8080/api/v1/healthcheck" >/dev/null 2>&1 && break
    sleep 5
done
log "Infisical ready"

# 10. Auto-sync from Infisical if credentials available
INFISICAL_CLIENT_ID=$(grep "^INFISICAL_CLIENT_ID=" "$ENV_FILE" | cut -d= -f2-)
if [ -n "$INFISICAL_CLIENT_ID" ]; then
    info "Running Infisical sync..."
    bash "$ROOT_DIR/secrets-sync/infisical-sync.sh" && \
        log "Infisical sync complete - all secrets updated" || \
        warn "Infisical sync failed"
else
    warn "No Infisical credentials - add --infisical-id and --infisical-secret to sync secrets"
fi

# 11. Link GitHub to OpenHands
info "Linking GitHub to OpenHands..."
GH_TOKEN=$(grep "^GITHUB_TOKEN=" "$ENV_FILE" | cut -d= -f2-)
GH_USER=$(grep "^GIT_USERNAME=" "$ENV_FILE" | cut -d= -f2-)
for attempt in 1 2 3 4 5; do
    sleep 15
    if curl -sf -X POST "http://localhost:3000/api/v1/secrets/git-providers" \
        -H "Content-Type: application/json" \
        -d "{\"provider_tokens\":{\"github\":{\"token\":\"$GH_TOKEN\",\"user_id\":\"$GH_USER\",\"host\":\"github.com\"}}}" \
        >/dev/null 2>&1; then
        log "GitHub linked to OpenHands (attempt $attempt)"
        break
    fi
    [ $attempt -eq 5 ] && warn "GitHub link failed - run infisical-sync.sh manually"
done

# 12. Summary
echo ""
echo -e "${GREEN}=========================================="
echo "   Install Complete!"
echo -e "==========================================${NC}"
echo ""
echo -e "  Dashboard:    ${BLUE}http://$HOST_IP${NC}"
echo -e "  Open WebUI:   ${BLUE}http://$HOST_IP:8888${NC}"
echo -e "  OpenHands:    ${BLUE}http://$HOST_IP:3000${NC}"
echo -e "  Infisical:    ${BLUE}http://$HOST_IP:8080${NC}"
echo -e "  LiteLLM:      ${BLUE}http://$HOST_IP:4000${NC}"
echo -e "  Crew:         ${BLUE}http://$HOST_IP:9002${NC}"
echo ""
if [ -z "$INFISICAL_CLIENT_ID" ]; then
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Open Infisical ($HOST_IP:8080) and add API keys:"
echo "     ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY"
echo "  2. Run: sudo bash $ROOT_DIR/secrets-sync/infisical-sync.sh"
echo "  3. Open Dashboard (:80) and select models for each agent"
fi
echo -e "  4. OpenHands (:3000) -> Settings -> LLM"
echo "     Model: openai/claude | Base URL: http://$HOST_IP:4000"
echo ""
