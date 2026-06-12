#!/usr/bin/env python3
"""
يسحب الأسرار من Infisical عبر Machine Identity (Universal Auth)
ويحدّث المفاتيح المُدارة داخل ملف .env.
يقرأ الإعدادات من متغيّرات البيئة (يمرّرها السكربت الأب).
"""
import os
import re
import json
import urllib.request
import urllib.error

API = os.environ.get("INFISICAL_API_URL", "http://localhost:8080").rstrip("/")
CID = os.environ["INFISICAL_CLIENT_ID"]
CSEC = os.environ["INFISICAL_CLIENT_SECRET"]
PID = os.environ["INFISICAL_PROJECT_ID"]
ENVSLUG = os.environ.get("INFISICAL_ENV", "dev")
ENV_FILE = os.environ["ENV_FILE"]
MANAGED = os.environ.get("MANAGED_KEYS", "").split()


def _request(method, url, data=None, headers=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    # 1) تسجيل الدخول بالهوية الآلية
    try:
        tok = _request(
            "POST",
            f"{API}/api/v1/auth/universal-auth/login",
            {"clientId": CID, "clientSecret": CSEC},
        )["accessToken"]
    except urllib.error.HTTPError as e:
        print("فشل تسجيل الدخول:", e.code, e.read().decode())
        raise SystemExit(1)
    except Exception as e:
        print("تعذّر الاتصال بـ Infisical:", e)
        raise SystemExit(1)

    # 2) جلب الأسرار
    url = (
        f"{API}/api/v3/secrets/raw"
        f"?workspaceId={PID}&environment={ENVSLUG}&secretPath=/"
    )
    try:
        data = _request("GET", url, headers={"Authorization": f"Bearer {tok}"})
    except urllib.error.HTTPError as e:
        print("فشل جلب الأسرار:", e.code, e.read().decode())
        raise SystemExit(1)

    secrets = {s["secretKey"]: s["secretValue"] for s in data.get("secrets", [])}

    # 3) تحديث المفاتيح المُدارة داخل .env
    lines = open(ENV_FILE, encoding="utf-8").read().splitlines()
    out, updated = [], set()
    for ln in lines:
        m = re.match(r"^([A-Z0-9_]+)=", ln)
        if m and m.group(1) in MANAGED and m.group(1) in secrets:
            key = m.group(1)
            out.append(f"{key}={secrets[key]}")
            updated.add(key)
        else:
            out.append(ln)
    for key in MANAGED:
        if key in secrets and key not in updated:
            out.append(f"{key}={secrets[key]}")
            updated.add(key)

    open(ENV_FILE, "w", encoding="utf-8").write("\n".join(out) + "\n")

    print("تم تحديث:", ", ".join(sorted(updated)) or "(لا شيء)")
    missing = [k for k in MANAGED if k not in secrets]
    if missing:
        print("غير موجودة في Infisical (تُجوهلت):", ", ".join(missing))


if __name__ == "__main__":
    main()
