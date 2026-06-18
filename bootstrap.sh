#!/usr/bin/env bash
#
# سكربت الإقلاع — تشغيل المنظومة بأمر واحد على الـ VM.
# الاستخدام (بصلاحية root):
#     sudo bash bootstrap.sh
#
# يقوم بـ: تثبيت git، استنساخ المستودع، ثم تشغيل install.sh.
#
set -euo pipefail

REPO_URL_HOST="github.com/menokemo/AI-company-.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-company}"
export INSTALL_DIR
TARGET="${INSTALL_DIR}"

err() { printf "\033[1;31m[x]\033[0m %s\n" "$*" >&2; }
log() { printf "\033[1;32m[+]\033[0m %s\n" "$*"; }

# التحقق من صلاحية root
if [ "$(id -u)" -ne 0 ]; then
  err "شغّل السكربت بصلاحية root:  sudo bash bootstrap.sh"
  exit 1
fi

# الأدوات المطلوبة
log "تجهيز الأدوات (git, curl)..."
apt-get update -y
apt-get install -y git curl ca-certificates

# استنساخ أو تحديث المستودع
if [ -d "$TARGET/.git" ]; then
  log "المستودع موجود — تحديثه..."
  git -C "$TARGET" pull --ff-only || true
else
  # طلب التوكن بإدخال مخفي (لا يُحفظ في سجل الأوامر)
  read -rsp "GitHub Token (إدخال مخفي): " GH_TOKEN; echo
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
exec ./install.sh
