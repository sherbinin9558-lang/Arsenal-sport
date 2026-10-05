"""T-Bank payment webhook.

The webhook never trusts a tenant or plan supplied by the browser. It resolves
the payment to the checkout session stored in Supabase, verifies the current
payment state with T-Bank, and only then activates the subscription.
"""

import hashlib
import hmac
import json
import os
import requests
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from tbank_billing import get_state, _token
from billing import get_payment

app = FastAPI(title="AI Agent Content Manager Billing Webhook")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_BODY_BYTES = 256 * 1024
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "billing-webhook"}


@app.get("/readyz")
async def readyz():
    url, key = _supabase()
    if not url or not key:
        raise HTTPException(status_code=503, detail="Webhook storage is not configured")
    if not _env("TBANK_WEBHOOK_SECRET") and not _env("YOOKASSA_WEBHOOK_SECRET"):
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")
    return {"ok": True, "service": "billing-webhook", "supabase": "configured"}


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

def _process_billing_event(provider, event_key, payment_id, status, tenant_id, plan, payment_method_id=None, payload=None):
    url, _ = _supabase()
    payload_hash = hashlib.sha256(
        json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    response = requests.post(
        f"{url}/rest/v1/rpc/process_billing_payment_event",
        headers=_headers(),
        json={
            "p_provider": provider,
            "p_event_key": event_key,
            "p_provider_payment_id": str(payment_id),
            "p_status": status,
            "p_tenant_id": str(tenant_id),
            "p_plan": str(plan),
            "p_provider_payment_method_id": payment_method_id,
            "p_payload_hash": payload_hash,
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError("Billing state transition failed")
    return response.json()


def _verify_webhook_secret(request: Request, env_name):
    expected = _env(env_name)
    if not expected:
        return False
    auth = request.headers.get("authorization", "")
    supplied = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


async def _read_body(request: Request):
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@app.post("/webhooks/tbank/payment-status")
async def payment_status(request: Request):
    secret_verified = _verify_webhook_secret(request, "TBANK_WEBHOOK_SECRET")
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
        if not expected_token or not hmac.compare_digest(str(supplied_token), str(expected_token)):
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    elif not secret_verified:
        raise HTTPException(status_code=401, detail="Webhook authentication required")

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

    event_key = f"tbank:{payment_id}:{status.lower()}"
    try:
        result = _process_billing_event(
            "tbank",
            event_key,
            payment_id,
            status,
            tenant,
            plan,
            payload=body,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Billing state transition failed")

    return {
        "ok": True,
        "payment_id": payment_id,
        "status": status,
        "plan": plan,
        "duplicate": bool((result or {}).get("duplicate")),
    }


@app.post("/webhooks/yookassa")
async def yookassa_payment_status(request: Request):
    _verify_webhook_secret(request, "YOOKASSA_WEBHOOK_SECRET")
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

    plan = str(checkout.get("plan") or "").lower()
    tenant = str(checkout.get("tenant_id") or "")
    if plan not in ("starter", "pro", "business") or not tenant:
        raise HTTPException(status_code=422, detail="Invalid checkout session")

    payment_method = payment.get("payment_method") or {}
    payment_method_id = payment_method.get("id") if payment_method.get("saved") else None
    event_key = f"yookassa:{event or 'payment.succeeded'}:{payment_id}:{status}"

    try:
        result = _process_billing_event(
            "yookassa",
            event_key,
            payment_id,
            status,
            tenant,
            plan,
            payment_method_id=payment_method_id,
            payload=body,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Billing state transition failed")

    return {
        "ok": True,
        "event": event,
        "payment_id": payment_id,
        "status": status,
        "plan": plan,
        "duplicate": bool((result or {}).get("duplicate")),
    }
