import json
import os
import sys
import time
import requests

BASE_URL = os.getenv("BILLING_WEBHOOK_URL", "").rstrip("/")
TIMEOUT = 30

if not BASE_URL:
    print("BILLING_WEBHOOK_URL is not configured; webhook smoke skipped.")
    raise SystemExit(0)

results = []
for path in ("/healthz", "/readyz"):
    started = time.perf_counter()
    try:
        r = requests.get(BASE_URL + path, timeout=TIMEOUT)
        item = {"path": path, "status": r.status_code, "latency_ms": round((time.perf_counter()-started)*1000,1), "body": r.text[:2000]}
    except Exception as exc:
        item = {"path": path, "status": 0, "error": f"{type(exc).__name__}: {exc}"}
    results.append(item)

print(json.dumps(results, ensure_ascii=False, indent=2))
if results[0]["status"] != 200 or results[1]["status"] != 200:
    sys.exit(1)
try:
    ready = json.loads(results[1]["body"])
except Exception:
    sys.exit(1)
if ready.get("ok") is not True:
    sys.exit(1)
