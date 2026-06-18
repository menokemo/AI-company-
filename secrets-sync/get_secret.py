#!/usr/bin/env python3
"""
يُعيد قيمة سرّ واحد من Infisical على stdout.
الاستخدام:  python3 get_secret.py SECRET_NAME
يقرأ إعدادات الاتصال من متغيّرات البيئة (يمرّرها السكربت الأب).
"""
import os, sys, json, urllib.request, urllib.error

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: get_secret.py SECRET_NAME", file=sys.stderr)
        sys.exit(1)

    secret_name = sys.argv[1]
    api  = os.environ.get("INFISICAL_URL", os.environ.get("INFISICAL_API_URL", "http://ai-infisical:8080")).rstrip("/")
    cid  = os.environ["INFISICAL_CLIENT_ID"]
    csec = os.environ["INFISICAL_CLIENT_SECRET"]
    pid  = os.environ["INFISICAL_PROJECT_ID"]
    env  = os.environ.get("INFISICAL_ENV", "dev")

    def req(method, url, data=None, headers=None):
        body = json.dumps(data).encode() if data else None
        r = urllib.request.Request(url, data=body, method=method)
        if data:
            r.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            r.add_header(k, v)
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.load(resp)

    try:
        tok = req("POST", f"{api}/api/v1/auth/universal-auth/login",
                  {"clientId": cid, "clientSecret": csec})["accessToken"]
    except Exception as e:
        print(f"فشل تسجيل الدخول: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = req("GET",
                   f"{api}/api/v3/secrets/raw/{secret_name}"
                   f"?workspaceId={pid}&environment={env}&secretPath=/",
                   headers={"Authorization": f"Bearer {tok}"})
        print(data["secret"]["secretValue"], end="")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"السرّ '{secret_name}' غير موجود في Infisical.", file=sys.stderr)
        else:
            print(f"خطأ: {e.code}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
