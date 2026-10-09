"""T-Bank (formerly Tinkoff) Internet Acquiring checkout."""
import hashlib, os, time, uuid, requests
import streamlit as st

def _cfg(name, default=""):
    try: value=st.secrets.get(name, os.getenv(name, default))
    except Exception: value=os.getenv(name, default)
    return str(value or "").strip()

TERMINAL_KEY=_cfg("TBANK_TERMINAL_KEY")
PASSWORD=_cfg("TBANK_PASSWORD")
PUBLIC_URL=_cfg("SAAS_PUBLIC_URL").rstrip("/")
API_URL="https://securepay.tinkoff.ru/v2"

def _save_checkout(tenant_id, order_id, payment_id, plan, expected_amount, expected_currency="RUB"):
    key=_cfg("SUPABASE_SERVICE_ROLE_KEY")
    url=_cfg("SUPABASE_URL").rstrip("/")
    if not key or not url:
        raise RuntimeError("Supabase checkout storage is not configured.")
    h={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=minimal"}
    r=requests.post(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=h,
        json={"tenant_id":str(tenant_id),"provider":"tbank","provider_order_id":str(order_id),
              "provider_payment_id":str(payment_id or ""),"plan":plan,"status":"created",
              "expected_amount":f"{float(expected_amount):.2f}","expected_currency":str(expected_currency).upper()},
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError("Не удалось сохранить checkout-сессию в платёжной базе.")

def configured():
    return bool(TERMINAL_KEY and PASSWORD and PUBLIC_URL)

def _token(data):
    values={k:v for k,v in data.items() if k not in ("Token","Receipt","DATA","Data","ForeignReceiver","Shops","Items") and v is not None}
    values["Password"]=PASSWORD
    raw="".join(str(values[k]) for k in sorted(values))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def plan_price(plan):
    raw=_cfg(f"SAAS_{plan.upper()}_PRICE")
    try: return float(raw.replace(",", "."))
    except Exception: return 0.0

def _receipt_for_checkout(plan, amount_kopecks):
    """Build a compliant receipt only when the merchant explicitly enables it."""
    enabled = _cfg("TBANK_RECEIPT_REQUIRED", "0").lower() in ("1", "true", "yes")
    if not enabled:
        return None

    taxation = _cfg("TBANK_RECEIPT_TAXATION")
    tax = _cfg("TBANK_RECEIPT_TAX", "none")
    contact_email = _cfg("TBANK_RECEIPT_EMAIL")
    contact_phone = _cfg("TBANK_RECEIPT_PHONE")
    if not taxation:
        raise RuntimeError("TBANK_RECEIPT_REQUIRED=1 требует TBANK_RECEIPT_TAXATION.")
    if not contact_email and not contact_phone:
        raise RuntimeError("TBANK_RECEIPT_REQUIRED=1 требует TBANK_RECEIPT_EMAIL или TBANK_RECEIPT_PHONE.")
    if tax not in ("none","vat0","vat5","vat7","vat10","vat22","vat105","vat107","vat110","vat122"):
        raise RuntimeError("Недопустимый TBANK_RECEIPT_TAX.")

    item = {
        "Name": f"Подписка AI Agent Content Manager · {plan.upper()}",
        "Price": int(amount_kopecks),
        "Quantity": 1,
        "Amount": int(amount_kopecks),
        "PaymentMethod": _cfg("TBANK_RECEIPT_PAYMENT_METHOD", "full_payment"),
        "PaymentObject": _cfg("TBANK_RECEIPT_PAYMENT_OBJECT", "service"),
        "Tax": tax,
    }
    receipt = {
        "Taxation": taxation,
        "Items": [item],
        "Payments": {"Electronic": int(amount_kopecks)},
    }
    if contact_email:
        receipt["Email"] = contact_email
    else:
        receipt["Phone"] = contact_phone
    return receipt


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
    receipt = _receipt_for_checkout(plan, int(round(price*100)))
    if receipt is not None:
        payload["Receipt"] = receipt
    notification_url = _cfg("TBANK_NOTIFICATION_URL")
    if notification_url:
        payload["NotificationURL"] = notification_url
    # T-Bank signs root scalar fields; nested DATA/Receipt are not included in Token.
    payload["Token"]=_token(payload)
    r=requests.post(f"{API_URL}/Init",json=payload,timeout=20)
    try: data=r.json()
    except Exception: data={"Message":r.text}
    if not r.ok or not data.get("Success"):
        raise RuntimeError(data.get("Message") or data.get("Details") or str(data))
    # The provider payment is already created at this point. Persist the
    # checkout record with bounded retries so a transient Supabase outage does
    # not strand a real payment without a durable application reference.
    save_error = None
    for attempt in range(3):
        try:
            _save_checkout(tenant_id, order_id, data.get("PaymentId"), plan, price, "RUB")
            save_error = None
            break
        except Exception as exc:
            save_error = exc
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
    if save_error is not None:
        raise RuntimeError(
            "Платёж в Т-Банке создан, но не удалось сохранить checkout-сессию. "
            f"Идентификатор заказа: {order_id}; payment: {data.get('PaymentId')}. "
            "Повторите синхронизацию checkout после восстановления Supabase."
        ) from save_error
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
