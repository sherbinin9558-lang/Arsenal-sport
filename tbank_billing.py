"""T-Bank (formerly Tinkoff) Internet Acquiring checkout."""
import hashlib, os, uuid, requests
import streamlit as st

def _cfg(name, default=""):
    try: value=st.secrets.get(name, os.getenv(name, default))
    except Exception: value=os.getenv(name, default)
    return str(value or "").strip()

TERMINAL_KEY=_cfg("TBANK_TERMINAL_KEY")
PASSWORD=_cfg("TBANK_PASSWORD")
PUBLIC_URL=_cfg("SAAS_PUBLIC_URL").rstrip("/")
API_URL="https://securepay.tinkoff.ru/v2"

def _save_checkout(tenant_id, order_id, payment_id, plan):
    key=_cfg("SUPABASE_SERVICE_ROLE_KEY")
    url=_cfg("SUPABASE_URL")
    if not key or not url: return
    h={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=minimal"}
    requests.post(f"{url}/rest/v1/billing_checkout_sessions",headers=h,json={"tenant_id":str(tenant_id),"provider":"tbank","provider_order_id":str(order_id),"provider_payment_id":str(payment_id or ""),"plan":plan,"status":"created"},timeout=15)

def configured():
    return bool(TERMINAL_KEY and PASSWORD and PUBLIC_URL)

def _token(data):
    values={k:v for k,v in data.items() if k not in ("Token","Receipt","DATA","Shops","Items") and v is not None}
    values["Password"]=PASSWORD
    raw="".join(str(values[k]) for k in sorted(values))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def plan_price(plan):
    raw=_cfg(f"SAAS_{plan.upper()}_PRICE")
    try: return float(raw.replace(",", "."))
    except Exception: return 0.0

def create_checkout(plan, tenant_id):
    price=plan_price(plan)
    if price <= 0: raise RuntimeError("Цена тарифа не настроена в Secrets.")
    if not configured(): raise RuntimeError("Т-Банк не настроен: нужны TBANK_TERMINAL_KEY, TBANK_PASSWORD и SAAS_PUBLIC_URL.")
    order_id=f"{str(tenant_id)[:12]}-{uuid.uuid4().hex[:16]}"
    payload={
        "TerminalKey":TERMINAL_KEY,
        "Amount":int(round(price*100)),
        "OrderId":order_id,
        "Description":f"Подписка AI Agent Content Manager · {plan.upper()}",
        "Language":"ru",
        "SuccessURL":f"{PUBLIC_URL}/?billing=tbank_return&order_id={order_id}",
        "FailURL":f"{PUBLIC_URL}/?billing=tbank_fail&order_id={order_id}",
        "DATA":{"tenant_id":str(tenant_id),"plan":plan},
    }
    # T-Bank signs root scalar fields; nested DATA is not included in Token.
    payload["Token"]=_token(payload)
    r=requests.post(f"{API_URL}/Init",json=payload,timeout=20)
    try: data=r.json()
    except Exception: data={"Message":r.text}
    if not r.ok or not data.get("Success"):
        raise RuntimeError(data.get("Message") or data.get("Details") or str(data))
    _save_checkout(tenant_id, order_id, data.get("PaymentId"), plan)
    return data

def get_state(payment_id):
    if not configured(): raise RuntimeError("Т-Банк не настроен.")
    payload={"TerminalKey":TERMINAL_KEY,"PaymentId":str(payment_id)}
    payload["Token"]=_token(payload)
    r=requests.post(f"{API_URL}/GetState",json=payload,timeout=20)
    try: data=r.json()
    except Exception: data={"Message":r.text}
    if not r.ok or not data.get("Success"):
        raise RuntimeError(data.get("Message") or data.get("Details") or str(data))
    return data


def get_checkout_by_order(order_id, tenant_id):
    key=_cfg("SUPABASE_SERVICE_ROLE_KEY")
    url=_cfg("SUPABASE_URL").rstrip("/")
    if not key or not url:
        raise RuntimeError("Supabase checkout storage is not configured.")
    h={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    r=requests.get(
        f"{url}/rest/v1/billing_checkout_sessions", headers=h,
        params={"select":"tenant_id,provider_payment_id,plan,status","provider":"eq.tbank",
                "provider_order_id":f"eq.{order_id}","tenant_id":f"eq.{tenant_id}","limit":"1"}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Не удалось получить checkout-сессию: {r.text}")
    rows=r.json()
    return rows[0] if rows else None
