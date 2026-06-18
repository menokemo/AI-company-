#!/usr/bin/env bash
#
# سكربت الإقلاع — تشغيل المنظومة بأمر واحد على الـ VM.
# الاستخدام (بصلاحية root):
#     sudo bash bootstrap.sh [--github-token TOKEN]
#
# يقوم بـ: تثبيت git، استنساخ المستودع، ثم تشغيل install.sh.
#
set -euo pipefail

REPO_URL_HOST="github.com/menokemo/AI-company-.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
export INSTALL_DIR
TARGET="${INSTALL_DIR}"
GH_TOKEN=""

err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }
log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }

# التحقق من صلاحية root
if [ "$(id -u)" -ne 0 ]; then
  err "شغّل السكربت بصلاحية root: sudo bash bootstrap.sh [--github-token TOKEN]"
  exit 1
fi

# معالجة الـ arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --github-token)
            GH_TOKEN="$2"
            shift 2
            ;;
        *)
            err "خيار غير معروف: $1"
            exit 1
            ;;
    esac
done

# الأدوات المطلوبة
log "تجهيز الأدوات (git, curl, docker)..."
apt-get update -y >/dev/null 2>&1
apt-get install -y git curl ca-certificates docker.io docker-compose python3 >/dev/null 2>&1

# استنساخ أو تحديث المستودع
if [ -d "$TARGET/.git" ]; then
  log "المستودع موجود — تحديثه..."
  git -C "$TARGET" pull --ff-only || true
else
  # طلب التوكن إذا لم يكن معطى
  if [ -z "$GH_TOKEN" ]; then
    read -rsp "GitHub Token (إدخال مخفي): " GH_TOKEN
    echo
  fi
  
  [ -z "$GH_TOKEN" ] && { err "GitHub Token مطلوب"; exit 1; }
  
  log "استنساخ المستودع..."
  git clone "https://${GH_TOKEN}@${REPO_URL_HOST}" "$TARGET"
  # إزالة التوكن من إعدادات git فورًا
  git -C "$TARGET" remote set-url origin "https://${REPO_URL_HOST}"
  unset GH_TOKEN
  log "تم الاستنساخ وإزالة التوكن من إعدادات git."
fi

# تشغيل المثبّت
cd "$TARGET"
chmod +x install.sh
log "تشغيل المثبّت..."

# تمرير token إلى install.sh إذا كان معطى
if [ -n "$GH_TOKEN" ]; then
  exec ./install.sh --github-token "$GH_TOKEN"
else
  # طلب token إذا لم يكن معطى
  read -rsp "GitHub Token: " GH_TOKEN
  echo
  exec ./install.sh --github-token "$GH_TOKEN"
fi
