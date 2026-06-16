#!/usr/bin/env python3
"""
يولّد ملفات إعداد OpenHands تلقائياً من .env بعد كل sync.
يُشغَّل بعد مزامنة Infisical مباشرةً.
"""
import os, json, pathlib, subprocess

STATE_DIR = os.environ.get("OPENHANDS_STATE_DIR", "/opt/ai-company/data/openhands")
ENV_FILE  = os.environ.get("ENV_FILE", "/opt/ai-company/infrastructure/.env")

# ── قراءة .env ──────────────────────────────────────────────────────
env = {}
with open(ENV_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

# ── اكتشاف IP الـ VM ──────────────────────────────────────────────
try:
    host_ip = subprocess.check_output(
        ["hostname", "-i"], text=True
    ).split()[0]
except Exception:
    host_ip = "192.168.2.29"

master_key  = env.get("LITELLM_MASTER_KEY", "")
github_token = env.get("GITHUB_TOKEN", "")
git_username = env.get("GIT_USERNAME", "")

# ── config.toml لـ OpenHands V1 ──────────────────────────────────
out_dir = pathlib.Path(STATE_DIR)
out_dir.mkdir(parents=True, exist_ok=True)

config_toml = out_dir / "config.toml"
config_toml.write_text(f"""[llm]
model = "openai/claude"
base_url = "http://{host_ip}:4000"
api_key = "{master_key}"

[core]
workspace_base = "/opt/workspace"
""", encoding="utf-8")

# ── git credentials ───────────────────────────────────────────────
if github_token:
    git_email = f"{git_username}@users.noreply.github.com"
    creds = out_dir / ".git-credentials"
    creds.write_text(
        f"https://{git_username}:{github_token}@github.com\n",
        encoding="utf-8"
    )
    gitconfig = out_dir / ".gitconfig"
    gitconfig.write_text(
        f"[user]\n\tname = {git_username}\n\temail = {git_email}\n"
        f"[credential]\n\thelper = store --file /.openhands/.git-credentials\n",
        encoding="utf-8"
    )
    try:
        os.chown(creds,    1000, 1000)
        os.chown(gitconfig, 1000, 1000)
    except PermissionError:
        pass

try:
    os.chown(config_toml, 1000, 1000)
    os.chown(out_dir, 1000, 1000)
except PermissionError:
    pass

print(f"✓ OpenHands config → {config_toml}")
print(f"  LLM: openai/claude @ http://{host_ip}:4000")
if github_token:
    print(f"  Git: {git_username}")
