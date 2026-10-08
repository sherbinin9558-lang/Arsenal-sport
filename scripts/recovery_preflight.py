"""Read-only recovery preflight for production acceptance.

This deliberately does not mutate production or pretend to perform a restore.
It verifies that the live Supabase project is reachable and that the repository
contains the migration/recovery evidence required before a real restore drill.
"""
import os
import sys
from pathlib import Path
import requests

url = os.getenv("SUPABASE_URL", "").rstrip("/")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
if not url or not key:
    print("Supabase recovery preflight skipped: credentials not configured.")
    raise SystemExit(0)

headers = {"apikey": key, "Authorization": f"Bearer {key}"}
checks = {}
for table in ("tenants", "subscriptions", "billing_checkout_sessions", "ai_usage_events"):
    r = requests.get(f"{url}/rest/v1/{table}?select=*&limit=1", headers=headers, timeout=20)
    checks[table] = r.status_code
    if r.status_code >= 500:
        raise SystemExit(f"Recovery preflight failed for {table}: HTTP {r.status_code}")

migration_dir = Path("supabase/migrations")
checks["migration_count"] = len(list(migration_dir.glob("*.sql"))) if migration_dir.exists() else 0
if checks["migration_count"] == 0:
    raise SystemExit("Recovery preflight failed: no Supabase migrations found")

print(checks)
print("Recovery preflight passed. A real backup restore remains a separate operational drill and is not simulated here.")
