"""T-Bank payment webhook.

The webhook never trusts a tenant or plan supplied by the browser. It resolves
the payment to the checkout session stored in Supabase, verifies the current
payment state with T-Bank, and only then activates the subscription.
"""

import os
import requests
from fastapi import FastAPI, Request, HTTPException

from tbank_billing import get_state, _token
from billing import get_payment

app = FastAPI(title="AI Agent Content Manager Billing Webhook")


def _env(name, default=""):
    return str(os.getenv(name, default) or "").strip()


def _supabase():
    return _env("SUPABASE_URL").rstrip("/"), _env("SUPABASE_SERVICE_ROLE_KEY")


def _headers():
    url, key = _supabase()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY не настроены.")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _checkout_by_provider_payment(provider, payment_id):
    url, _ = _supabase()
    response = requests.get(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=_headers(),
        params={
            "select": "tenant_id,provider_order_id,provider_payment_id,plan,status",
            "provider": f"eq.{provider}",
            "provider_payment_id": f"eq.{payment_id}",
            "limit": "1",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None

def _checkout_by_payment(payment_id):
    url, _ = _supabase()
    rows = requests.get(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=_headers(),
        params={
            "select": "tenant_id,provider_order_id,provider_payment_id,plan,status",
            "provider": "eq.tbank",
            "provider_payment_id": f"eq.{payment_id}",
            "limit": "1",
        },
        timeout=15,
    )
    rows.raise_for_status()
    data = rows.json()
    return data[0] if data else None


def _update_checkout_provider_payment(provider, payment_id, status):
    url, _ = _supabase()
    response = requests.patch(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=_headers(),
        params={
            "provider": f"eq.{provider}",
            "provider_payment_id": f"eq.{payment_id}",
        },
        json={"status": status},
        timeout=15,
    )
    response.raise_for_status()

def _update_checkout(payment_id, status):
    url, _ = _supabase()
    response = requests.patch(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=_headers(),
        params={
            "provider": "eq.tbank",
            "provider_payment_id": f"eq.{payment_id}",
        },
        json={"status": status},
        timeout=15,
    )
    response.raise_for_status()


def _verify_webhook_secret(request: Request):
    expected = _env("TBANK_WEBHOOK_SECRET")
    if expected:
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {expected}":
            raise HTTPException(status_code=401, detail="Unauthorized")


async def _read_body(request: Request):
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@app.post("/webhooks/tbank/payment-status")
async def payment_status(request: Request):
    _verify_webhook_secret(request)
    body = await _read_body(request)

    payment_id = body.get("PaymentId") or body.get("PaymentID")
    if not payment_id:
        raise HTTPException(status_code=400, detail="PaymentId is required")

    # If T-Bank provides its notification Token, verify it as well.
    supplied_token = body.get("Token")
    if supplied_token:
        try:
            expected_token = _token(body)
        except Exception:
            expected_token = ""
        if supplied_token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid webhook token")

    payment_id = str(payment_id)
    checkout = _checkout_by_payment(payment_id)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    state = get_state(payment_id)
    status = str(state.get("Status") or "").upper()
    plan = str(checkout.get("plan") or "").lower()
    tenant = str(checkout.get("tenant_id") or "")

    if plan not in ("starter", "pro", "business") or not tenant:
        raise HTTPException(status_code=422, detail="Invalid checkout session")

    if status in ("CONFIRMED", "AUTHORIZED"):
        # Import here so this service remains independently deployable.
        from saas_core import activate_paid_subscription

        try:
            activate_paid_subscription(
                plan,
                payment_id,
                None,
                provider="tbank",
                tenant=tenant,
            )
            _update_checkout(payment_id, "confirmed")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Subscription activation failed: {exc}")
    elif status in ("CANCELED", "REJECTED", "DEADLINE_EXPIRED"):
        _update_checkout(payment_id, status.lower())
    else:
        _update_checkout(payment_id, status.lower() or "unknown")

    return {
        "ok": True,
        "payment_id": payment_id,
        "status": status,
        "tenant_id": tenant,
        "plan": plan,
    }


@app.post("/webhooks/yookassa")
async def yookassa_payment_status(request: Request):
    _verify_webhook_secret(request)
    body = await _read_body(request)
    event = str(body.get("event") or "").lower()
    obj = body.get("object") or {}
    payment_id = str(obj.get("id") or "")
    if not payment_id:
        raise HTTPException(status_code=400, detail="Payment id is required")

    # Authenticate the event by querying the payment directly with YooKassa.
    payment = get_payment(payment_id)
    status = str(payment.get("status") or "").lower()
    if status != "succeeded":
        return {"ok": True, "payment_id": payment_id, "status": status}

    checkout = _checkout_by_provider_payment("yookassa", payment_id)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    if str(checkout.get("status") or "").lower() == "confirmed":
        return {"ok": True, "payment_id": payment_id, "status": "confirmed"}

    plan = str(checkout.get("plan") or "").lower()
    tenant = str(checkout.get("tenant_id") or "")
    if plan not in ("starter", "pro", "business") or not tenant:
        raise HTTPException(status_code=422, detail="Invalid checkout session")

    payment_method = payment.get("payment_method") or {}
    payment_method_id = payment_method.get("id") if payment_method.get("saved") else None

    try:
        from saas_core import activate_paid_subscription
        activate_paid_subscription(
            plan,
            payment_id,
            payment_method_id,
            provider="yookassa",
            tenant=tenant,
        )
        _update_checkout_provider_payment("yookassa", payment_id, "confirmed")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Subscription activation failed: {exc}")

    return {
        "ok": True,
        "event": event,
        "payment_id": payment_id,
        "status": status,
        "tenant_id": tenant,
        "plan": plan,
    }
