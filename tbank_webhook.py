"""YooKassa billing webhook for SaaS subscriptions.

The webhook verifies payment/refund state with YooKassa and uses the database
state machine for idempotent subscription changes."""

import hashlib
import hmac
import json
import os
from decimal import Decimal, InvalidOperation
import requests
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


from billing import get_payment, get_refund, _save_checkout

app = FastAPI(title="AI Agent Content Manager Billing Webhook")

class RequestBodyTooLarge(Exception):
    """Raised when an incoming webhook body exceeds the hard limit."""
    pass

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

class RequestSizeLimitMiddleware:
    """ASGI body-size guard; also covers chunked requests without Content-Length."""
    MAX_BODY_BYTES = 256 * 1024

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.MAX_BODY_BYTES:
                    response = JSONResponse(status_code=413, content={"detail": "Request too large"})
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
                await response(scope, receive, send)
                return

        total = 0
        finished = False

        async def limited_receive():
            nonlocal total, finished
            if finished:
                return {"type": "http.disconnect"}
            message = await receive()
            if message.get("type") == "http.request":
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > self.MAX_BODY_BYTES:
                    finished = True
                    raise RequestBodyTooLarge()
                if not message.get("more_body", False):
                    finished = True
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(status_code=413, content={"detail": "Request too large"})
            await response(scope, receive, send)

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
    yookassa_ready = bool(_env("YOO_KASSA_SHOP_ID") and _env("YOO_KASSA_SECRET_KEY"))
    if not yookassa_ready:
        raise HTTPException(status_code=503, detail="YooKassa provider configuration is missing")
    return {
        "ok": True,
        "service": "billing-webhook",
        "supabase": "configured",
        "yookassa": "configured",
    }

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
            "select": "tenant_id,provider_order_id,provider_payment_id,plan,status,expected_amount,expected_currency",
            "provider": f"eq.{provider}",
            "provider_payment_id": f"eq.{payment_id}",
            "limit": "1",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None

def _verify_yookassa_payment_amount(payment, checkout):
    """Require provider settlement amount/currency to match the server-created checkout."""
    expected_amount = checkout.get("expected_amount")
    expected_currency = str(checkout.get("expected_currency") or "").upper()
    actual = payment.get("amount") if isinstance(payment, dict) else None
    actual_amount = actual.get("value") if isinstance(actual, dict) else None
    actual_currency = str(actual.get("currency") or "").upper() if isinstance(actual, dict) else ""
    try:
        expected = Decimal(str(expected_amount))
        received = Decimal(str(actual_amount))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Checkout amount verification failed")
    if not expected.is_finite() or not received.is_finite() or expected <= 0 or received != expected:
        raise HTTPException(status_code=422, detail="Checkout amount verification failed")
    if not expected_currency or actual_currency != expected_currency:
        raise HTTPException(status_code=422, detail="Checkout currency verification failed")

def _recover_checkout_from_provider(payment):
    """Recreate a missing checkout row only from verified, settled provider metadata.

    This is the recovery path for the case where YooKassa created a payment but
    Supabase failed to persist the initial checkout record. The caller must have
    fetched this payment directly from YooKassa before calling this function.
    """
    if not isinstance(payment, dict) or str(payment.get("status") or "").lower() not in ("succeeded", "confirmed"):
        raise HTTPException(status_code=404, detail="Checkout session not found")
    metadata = payment.get("metadata")
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=404, detail="Checkout session not found")
    checkout_id = str(metadata.get("checkout_id") or "").strip()
    tenant_id = str(metadata.get("tenant_id") or "").strip()
    plan = str(metadata.get("plan") or "").lower().strip()
    expected_amount = metadata.get("expected_amount")
    expected_currency = str(metadata.get("expected_currency") or "").upper().strip()
    payment_id = str(payment.get("id") or "").strip()
    if not checkout_id or not tenant_id or not payment_id or plan not in ("starter", "pro", "business"):
        raise HTTPException(status_code=422, detail="Invalid provider checkout metadata")
    if expected_currency != "RUB":
        raise HTTPException(status_code=422, detail="Checkout currency verification failed")
    recovery_checkout = {"expected_amount": expected_amount, "expected_currency": expected_currency}
    _verify_yookassa_payment_amount(payment, recovery_checkout)
    try:
        _save_checkout(tenant_id, checkout_id, payment_id, plan, expected_amount, expected_currency)
    except Exception:
        # A concurrent webhook may already have restored the same row. Only
        # continue if the durable row is now present; otherwise ask YooKassa
        # to retry rather than acknowledging an unrecorded payment.
        existing = _checkout_by_provider_payment("yookassa", payment_id)
        if not existing:
            raise HTTPException(status_code=503, detail="Checkout recovery is temporarily unavailable")
        return existing
    recovered = _checkout_by_provider_payment("yookassa", payment_id)
    if not recovered:
        raise HTTPException(status_code=503, detail="Checkout recovery is temporarily unavailable")
    return recovered



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
    """Validate an optional additional Bearer secret for provider notifications."""
    expected = _env(env_name)
    if not expected:
        return False
    auth = request.headers.get("authorization", "").strip()
    if not auth:
        return False
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    supplied = auth[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


async def _read_body(request: Request):
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@app.post("/webhooks/yookassa")
async def yookassa_payment_status(request: Request):
    # Standard YooKassa HTTP notifications do not provide a configurable shared
    # Bearer header. If our optional extra secret is supplied, validate it;
    # otherwise authenticate by fetching the payment/refund from YooKassa.
    _verify_webhook_secret(request, "YOOKASSA_WEBHOOK_SECRET")
    body = await _read_body(request)
    event = str(body.get("event") or "").strip().lower()
    obj = body.get("object")
    if not isinstance(obj, dict):
        raise HTTPException(status_code=400, detail="Invalid notification object")
    if not (event.startswith("payment.") or event.startswith("refund.")):
        raise HTTPException(status_code=400, detail="Unsupported notification event")

    is_refund = event.startswith("refund.")
    if is_refund:
        refund_id = str(obj.get("id") or "").strip()
        payment_id = str(obj.get("payment_id") or "").strip()
        if not refund_id or not payment_id:
            raise HTTPException(status_code=400, detail="Refund and payment ids are required")
        # A refund notification is not authoritative by itself. Fetch the refund
        # from YooKassa and bind it to the original payment before changing access.
        refund = get_refund(refund_id)
        if str(refund.get("payment_id") or "") != payment_id:
            raise HTTPException(status_code=400, detail="Refund/payment mismatch")
        refund_status = str(refund.get("status") or "").lower()
        if refund_status == "succeeded":
            status = "refunded"
        elif refund_status == "canceled":
            status = "refund_canceled"
        else:
            status = "refund_pending"
        payment = get_payment(payment_id)
        provider_status = str(payment.get("status") or "").lower()
    else:
        payment_id = str(obj.get("id") or "").strip()
        if not payment_id:
            raise HTTPException(status_code=400, detail="Payment id is required")
        # Verify current payment status directly; do not trust status in the body.
        payment = get_payment(payment_id)
        provider_status = str(payment.get("status") or "").lower()
        status = provider_status
        refund_id = ""

    checkout = _checkout_by_provider_payment("yookassa", payment_id)
    if not checkout:
        checkout = _recover_checkout_from_provider(payment)

    if not is_refund and provider_status in ("succeeded", "confirmed"):
        _verify_yookassa_payment_amount(payment, checkout)
    plan = str(checkout.get("plan") or "").lower()
    tenant = str(checkout.get("tenant_id") or "")
    if plan not in ("starter", "pro", "business") or not tenant:
        raise HTTPException(status_code=422, detail="Invalid checkout session")

    payment_method = payment.get("payment_method") or {}
    payment_method_id = payment_method.get("id") if payment_method.get("saved") else None
    # Include refund id so two distinct refunds for one payment do not collide.
    event_object_id = refund_id if is_refund else payment_id
    event_key = f"yookassa:{event}:{event_object_id}:{status}"

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
        "provider_status": provider_status,
        "plan": plan,
        "duplicate": bool((result or {}).get("duplicate")),
    }
