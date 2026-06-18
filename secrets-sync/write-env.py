#!/usr/bin/env python3
"""Write .env file cleanly from key=value arguments."""
import sys
import os

install_dir = os.environ.get("INSTALL_DIR", "/opt/ai-company")
env_file = os.path.join(install_dir, "infrastructure", ".env")
pairs = {}

for arg in sys.argv[1:]:
    if arg.startswith("ENV_FILE="):
        env_file = arg.split("=",1)[1]
    elif "=" in arg:
        k, _, v = arg.partition("=")
        pairs[k.strip()] = v

# Read existing values to preserve any extras not in args
existing = {}
try:
    for line in open(env_file):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k,_,v = line.partition("=")
            existing[k.strip()] = v
except: pass

# Merge: args override existing
merged = {**existing, **pairs}

# Write clean .env
lines = ["# AI Company - Environment Variables\n"]
for k, v in merged.items():
    if not k.startswith("#"):
        lines.append(f"{k}={v}\n")

open(env_file, "w").writelines(lines)
print(f"  .env written ({len(merged)} variables)")
