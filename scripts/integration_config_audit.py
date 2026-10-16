"""Read-only audit of production integration configuration."""
import json, os, re
from pathlib import Path

def present(name): return bool(str(os.getenv(name,"") or "").strip())
def url_shape(value): return bool(re.fullmatch(r"https://[^/\s]+(?:/[^\s]*)?",str(value or "").strip()))

def run():
    checks={
      "supabase_url":present("SUPABASE_URL"),"supabase_anon_key":present("SUPABASE_ANON_KEY"),
      "supabase_service_role_key":present("SUPABASE_SERVICE_ROLE_KEY"),"billing_webhook_url":present("BILLING_WEBHOOK_URL"),
      "billing_webhook_url_https":url_shape(os.getenv("BILLING_WEBHOOK_URL")) if present("BILLING_WEBHOOK_URL") else None,
      "tbank_credentials":present("TBANK_TERMINAL_KEY") and present("TBANK_PASSWORD"),
      "yookassa_credentials":present("YOOKASSA_SHOP_ID") and present("YOOKASSA_SECRET_KEY"),
      "telegram_token":present("TELEGRAM_BOT_TOKEN") or present("TELEGRAM_TOKEN"),
      "telegram_channel":present("TELEGRAM_CHANNEL"),"vk_token":present("VK_ACCESS_TOKEN") or present("VK_TOKEN"),
      "sentry_dsn_optional":True}
    required=["supabase_url","supabase_anon_key"]; failures=[n for n in required if not checks[n]]
    result={"checks":checks,"required_failures":failures,"status":"PASS" if not failures else "FAIL"}
    Path("artifacts").mkdir(exist_ok=True); Path("artifacts/integration-config.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(run())
