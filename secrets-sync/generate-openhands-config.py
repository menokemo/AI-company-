#!/usr/bin/env python3
"""
يولّد ملف settings.json لـ OpenHands تلقائياً من .env.
يُشغَّل بعد مزامنة Infisical مباشرةً.
"""
import os, json, pathlib, stat

STATE_DIR = os.environ.get(
    "OPENHANDS_STATE_DIR",
    "/opt/ai-company/data/openhands-state"
)
ENV_FILE = os.environ.get(
    "ENV_FILE",
    "/opt/ai-company/infrastructure/.env"
)

# ── قراءة .env ──────────────────────────────────────────────────────
env = {}
with open(ENV_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

# ── بناء الإعدادات ───────────────────────────────────────────────────
settings = {
    "llm_model":      "openai/claude",
    "llm_base_url":   "http://ai-litellm:4000",
    "llm_api_key":    env.get("LITELLM_MASTER_KEY", ""),
    "github_token":   env.get("GITHUB_TOKEN", ""),
    "git_username":   env.get("GIT_USERNAME", ""),
    "agent":          "CodeActAgent",
    "language":       "en",
}

# إزالة القيم الفارغة
settings = {k: v for k, v in settings.items() if v}

# ── كتابة الملف ──────────────────────────────────────────────────────
out_dir  = pathlib.Path(STATE_DIR)
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "settings.json"

out_file.write_text(
    json.dumps(settings, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# ملكية uid 1000 عشان OpenHands يقدر يقراه
try:
    os.chown(out_file, 1000, 1000)
    os.chown(out_dir,  1000, 1000)
except PermissionError:
    pass  # لو مش root، ده طبيعي

print(f"✓ OpenHands settings → {out_file}")
keys_set = [k for k in settings if k != "agent" and k != "language"]
print(f"  المفاتيح المُعيَّنة: {', '.join(keys_set)}")
