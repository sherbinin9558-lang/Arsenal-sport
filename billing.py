"""YooKassa checkout integration for SaaS subscriptions.

Secrets:
YOO_KASSA_SHOP_ID
YOO_KASSA_SECRET_KEY
SAAS_PUBLIC_URL
SAAS_STARTER_PRICE
SAAS_PRO_PRICE
SAAS_BUSINESS_PRICE

The app creates a redirect checkout. Subscription activation is performed only
after YooKassa reports a successful payment.
"""
import math, os, time, uuid, requests
import streamlit as st

PLANS = {
    "starter": {"name":"STARTER", "secret":"SAAS_STARTER_PRICE"},
    "pro": {"name":"PRO", "secret":"SAAS_PRO_PRICE"},
    "business": {"name":"BUSINESS", "secret":"SAAS_BUSINESS_PRICE"},
}

def _cfg(name, default=""):
    try:
        value=st.secrets.get(name, os.getenv(name, default))
    except Exception:
        value=os.getenv(name, default)
    return str(value or "").strip()

SHOP_ID=_cfg("YOO_KASSA_SHOP_ID")
SECRET_KEY=_cfg("YOO_KASSA_SECRET_KEY")
PUBLIC_URL=_cfg("SAAS_PUBLIC_URL").rstrip("/")

def _save_checkout(tenant_id, checkout_id, payment_id, plan):
    key=_cfg("SUPABASE_SERVICE_ROLE_KEY")
    url=_cfg("SUPABASE_URL").rstrip("/")
    if not key or not url:
        raise RuntimeError("Supabase checkout storage is not configured.")
    headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    r=requests.post(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=headers,
        json={
            "tenant_id": str(tenant_id),
            "provider": "yookassa",
            "provider_order_id": str(checkout_id),
            "provider_payment_id": str(payment_id),
            "plan": plan,
            "status": "created",
        },
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError("Не удалось сохранить checkout-сессию в хранилище.")

def get_checkout_by_order(checkout_id, tenant_id=None):
    key=_cfg("SUPABASE_SERVICE_ROLE_KEY")
    url=_cfg("SUPABASE_URL").rstrip("/")
    if not key or not url:
        raise RuntimeError("Supabase checkout storage is not configured.")
    headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    r=requests.get(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=headers,
        params={"select":"tenant_id,provider_payment_id,plan,status","provider":"eq.yookassa","provider_order_id":f"eq.{checkout_id}",**({"tenant_id":f"eq.{tenant_id}"} if tenant_id is not None else {}),"limit":"1"},
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError("Не удалось получить checkout-сессию из хранилища.")
    rows=r.json()
    return rows[0] if rows else None

def configured():
    return bool(SHOP_ID and SECRET_KEY and PUBLIC_URL)

def plan_price(plan):
    if plan not in PLANS:
        raise ValueError("Недопустимый тариф.")
    raw=_cfg(PLANS[plan]["secret"])
    try:
        value = float(raw.replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        return 0.0
    # Reject NaN/Infinity as well as zero/negative prices before building a
    # provider request. Non-finite floats can bypass a simple value <= 0 check.
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return value

def create_checkout(plan, tenant_id):
    price=plan_price(plan)
    if price <= 0:
        raise RuntimeError("Цена тарифа не настроена в Secrets.")
    if not configured():
        raise RuntimeError("ЮKassa не настроена: нужны YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY и SAAS_PUBLIC_URL.")
    if not _cfg("SUPABASE_SERVICE_ROLE_KEY") or not _cfg("SUPABASE_URL"):
        raise RuntimeError("Не настроено серверное сохранение checkout: нужны SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY.")
    checkout_id=str(uuid.uuid4())
    payload={
        "amount":{"value":f"{price:.2f}","currency":"RUB"},
        "capture":True,
        # Recurring charges are not implemented; never request saved payment methods.
        "save_payment_method": False,
        "confirmation":{"type":"redirect","return_url":f"{PUBLIC_URL}/?billing=return&checkout_id={checkout_id}"},
        "description":f"Подписка AI Agent Content Manager · {PLANS[plan]['name']}",
        "metadata":{"tenant_id":tenant_id,"plan":plan,"checkout_id":checkout_id},
    }
    r=requests.post(
        "https://api.yookassa.ru/v3/payments",
        auth=(SHOP_ID,SECRET_KEY),
        headers={"Idempotence-Key":checkout_id,"Content-Type":"application/json"},
        json=payload,
        timeout=20,
    )
    try: data=r.json()
    except Exception: data={"description":r.text}
    if not r.ok:
        # Provider response bodies are not safe to display or log verbatim.
        raise RuntimeError("ЮKassa не смогла создать платёж. Проверьте настройки и журнал провайдера.")
    confirmation=(data.get("confirmation") or {}).get("confirmation_url")
    if not confirmation:
        raise RuntimeError("ЮKassa не вернула ссылку на оплату.")
    # The provider payment already exists at this point. Retry the durable
    # local record a small, bounded number of times so a transient Supabase
    # failure does not strand a real payment without an application record.
    save_error = None
    for attempt in range(3):
        try:
            _save_checkout(tenant_id, checkout_id, data.get("id"), plan)
            save_error = None
            break
        except Exception as exc:
            save_error = exc
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
    if save_error is not None:
        raise RuntimeError(
            "Платёж в ЮKassa создан, но не удалось сохранить checkout-сессию. "
            f"Идентификатор checkout: {checkout_id}; payment: {data.get('id')}. "
            "Повторите синхронизацию checkout после восстановления Supabase."
        ) from save_error
    return data

def get_payment(payment_id):
    if not configured():
        raise RuntimeError("ЮKassa не настроена.")
    r=requests.get(
        f"https://api.yookassa.ru/v3/payments/{payment_id}",
        auth=(SHOP_ID,SECRET_KEY),
        timeout=20,
    )
    try: data=r.json()
    except Exception: data={"description":r.text}
    if not r.ok:
        # Do not leak raw provider responses, which may contain sensitive data.
        raise RuntimeError("Не удалось проверить состояние платежа в ЮKassa.")
    return data
