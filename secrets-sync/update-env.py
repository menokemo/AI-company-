#!/usr/bin/env python3
"""Update specific keys in .env file without touching others."""
import sys, re, os

# Parse args: KEY=VALUE pairs + ENV_FILE=path
install_dir = os.environ.get("INSTALL_DIR", "/opt/ai-company")
env_file = os.path.join(install_dir, "infrastructure", ".env")
updates = {}
for arg in sys.argv[1:]:
    if arg.startswith("ENV_FILE="):
        env_file = arg.split("=", 1)[1]
    elif "=" in arg:
        k, _, v = arg.partition("=")
        updates[k] = v

try:
    content = open(env_file).read()
except:
    content = ""

for k, v in updates.items():
    if re.search(f"^{k}=", content, re.MULTILINE):
        content = re.sub(f"^{k}=.*", f"{k}={v}", content, flags=re.MULTILINE)
    else:
        content += f"\n{k}={v}"

open(env_file, "w").write(content)
print(f"Updated {list(updates.keys())} in {env_file}")
