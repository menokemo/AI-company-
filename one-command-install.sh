#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Company — One Command Complete Installation
# ══════════════════════════════════════════════════════════════════════════════
# Run with:
#   sudo bash one-command-install.sh [--github-token TOKEN]
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${BLUE}[→]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# Configuration
INSTALL_DIR="/opt/ai-company"
GITHUB_TOKEN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --github-token)
            GITHUB_TOKEN="$2"
            shift 2
            ;;
        *)
            err "Unknown option: $1"
            ;;
    esac
done

# Check root
if [ "$(id -u)" -ne 0 ]; then
    err "This script must run with sudo:\n  sudo bash one-command-install.sh"
fi

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     AI Company — Complete Installation (One Command)         ║"
echo "║                      v1.7.1                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Ask for GitHub Token
if [ -z "$GITHUB_TOKEN" ]; then
    info "GitHub Token required"
    echo ""
    echo "Get your token from: https://github.com/settings/tokens"
    echo "Required scopes: repo, read:user"
    echo ""
    read -rsp "GitHub Token (hidden): " GITHUB_TOKEN
    echo ""
    [ -z "$GITHUB_TOKEN" ] && err "GitHub Token is required"
fi
log "GitHub Token received"

# Step 2: Update system
info "Updating system packages..."
apt-get update -y >/dev/null 2>&1 || true
log "System updated"

# Step 3: Install dependencies
info "Installing dependencies..."
apt-get install -y \
    git \
    curl \
    ca-certificates \
    docker.io \
    docker-compose \
    python3 \
    openssl \
    >/dev/null 2>&1 || true
log "Dependencies installed"

# Step 4: Add user to docker group
info "Configuring Docker permissions..."
SUDO_USER=${SUDO_USER:-$(logname 2>/dev/null || echo 'root')}
if [ "$SUDO_USER" != "root" ]; then
    if ! groups "$SUDO_USER" 2>/dev/null | grep -q docker; then
        usermod -aG docker "$SUDO_USER"
        log "Added $SUDO_USER to docker group"
    fi
fi
log "Docker permissions configured"

# Step 5: Stop old services (if exist)
if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/infrastructure/docker-compose.yml" ]; then
    warn "Found existing installation - stopping services..."
    docker compose -f "$INSTALL_DIR/infrastructure/docker-compose.yml" down -v 2>/dev/null || true
    sleep 2
    log "Old services stopped"
fi

# Step 6: Make sure we have fresh install directory
info "Preparing installation directory..."
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Repository found - will update"
else
    info "Creating fresh directory..."
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    mkdir -p "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    log "Directory ready"
fi

# Step 7: Run install.sh (handles everything - clone/update/install)
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
info "Starting full installation..."
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

export INSTALL_DIR
cd "$INSTALL_DIR"

# Ensure install.sh exists
if [ ! -f "install.sh" ]; then
    info "Cloning repository first..."
    git clone https://github.com/menokemo/AI-company-.git . || err "Failed to clone repository"
    log "Repository cloned"
fi

# Make executable
chmod +x install.sh

# Run installation
bash install.sh --github-token "$GITHUB_TOKEN" || err "Installation failed"

# Success
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation Completed Successfully!           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📊 Status:"
echo "  Directory: $INSTALL_DIR"
echo "  Services: docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml ps"
echo ""
echo "🌐 Access:"
echo "  URL: http://$(hostname -I | awk '{print $1}'):8888"
echo ""
echo "📝 Useful commands:"
echo "  Logs:      docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml logs -f"
echo "  Restart:   docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml restart"
echo "  Stop:      docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml down"
echo ""

