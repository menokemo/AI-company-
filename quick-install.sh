#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Company — One Command Full Installation
# ══════════════════════════════════════════════════════════════════════════════
# Usage: sudo bash quick-install.sh [--github-token TOKEN] [--install-dir PATH]
#
# يقوم بـ كل شيء:
#   1. تثبيت جميع المتطلبات
#   2. استنساخ البرنامج من GitHub
#   3. إعداد البيئة
#   4. تشغيل التثبيت الكامل
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

# Default values
INSTALL_DIR="/opt/ai-company"
GITHUB_TOKEN=""
REPO_URL="github.com/menokemo/AI-company-.git"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --github-token)
            GITHUB_TOKEN="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        *)
            err "Unknown option: $1\nUsage: sudo bash quick-install.sh [--github-token TOKEN] [--install-dir PATH]"
            ;;
    esac
done

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    err "This script must be run with sudo:\n  sudo bash quick-install.sh"
fi

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        AI Company — One Command Full Installation            ║"
echo "║                      v1.7.1                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Ask for GitHub Token if not provided
if [ -z "$GITHUB_TOKEN" ]; then
    info "GitHub Token required"
    echo ""
    echo "Get your token from: https://github.com/settings/tokens"
    echo "  - Scopes: repo, read:user"
    echo ""
    read -rsp "GitHub Token (hidden): " GITHUB_TOKEN
    echo ""
fi

[ -z "$GITHUB_TOKEN" ] && err "GitHub Token is required"
log "GitHub Token received"

# Step 2: Install dependencies
info "Installing dependencies..."
apt-get update -y >/dev/null 2>&1 || true
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

# Step 3: Cleanup old installation (if exists)
if [ -d "$INSTALL_DIR" ]; then
    warn "Cleaning up old installation at $INSTALL_DIR..."
    
    # Stop Docker services
    if docker compose -f "$INSTALL_DIR/infrastructure/docker-compose.yml" ps >/dev/null 2>&1; then
        docker compose -f "$INSTALL_DIR/infrastructure/docker-compose.yml" down -v 2>/dev/null || true
    fi
    
    # Wait a bit for cleanup
    sleep 2
    
    # Remove old files
    rm -rf "$INSTALL_DIR"
fi

# Step 4: Clone repository
info "Cloning repository from GitHub..."
REPO_AUTH_URL="https://${GITHUB_TOKEN}@${REPO_URL}"
git clone "$REPO_AUTH_URL" "$INSTALL_DIR" >/dev/null 2>&1
log "Repository cloned"

# Step 5: Secure git configuration
info "Securing git configuration..."
cd "$INSTALL_DIR"
git remote set-url origin "https://${REPO_URL}"
log "Git secured (token removed from config)"

# Step 6: Setup environment
info "Setting up environment..."
cp .env.example .env
chmod 600 .env
log "Environment file created"

# Step 7: Configure Docker permissions
info "Configuring Docker permissions..."
CURRENT_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
if [ -n "$CURRENT_USER" ] && [ "$CURRENT_USER" != "root" ]; then
    if ! groups "$CURRENT_USER" 2>/dev/null | grep -q docker; then
        usermod -aG docker "$CURRENT_USER"
        warn "Added $CURRENT_USER to docker group"
        warn "You may need to log out and back in for changes to take effect"
    fi
fi
log "Docker permissions configured"

# Step 8: Make scripts executable
chmod +x install.sh
chmod +x bootstrap.sh
log "Scripts are executable"

# Step 9: Run installation
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
info "Starting full installation..."
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Set environment variables for install.sh
export INSTALL_DIR
cd "$INSTALL_DIR"

# Run install.sh with token
bash install.sh --github-token "$GITHUB_TOKEN"

# Success message
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation completed successfully!           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Wait for all Docker services to start (1-2 minutes)"
echo "  2. Open browser: http://$(hostname -I | awk '{print $1}'):8888"
echo "  3. Login with OpenWebUI credentials"
echo "  4. Start using AI Company!"
echo ""
echo "Useful commands:"
echo "  View services:  docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml ps"
echo "  View logs:      docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml logs -f"
echo "  Restart:        docker compose -f $INSTALL_DIR/infrastructure/docker-compose.yml restart"
echo ""
