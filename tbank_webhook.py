"""T-Bank payment webhook.

The webhook never trusts a tenant or plan supplied by the browser. It resolves
the payment to the checkout session stored in Supabase, verifies the current
payment state with T-Bank, and only then activates the subscription.
"""

import hashlib
import hmac
import json
import os
from decimal import Decimal, InvalidOperation
import requests
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from tbank_billing import get_state, _token
from billing import get_payment, get_refund

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
    tbank_ready = bool(_env("TBANK_TERMINAL_KEY") and _env("TBANK_PASSWORD"))
    # Readiness must reflect the credentials required for authoritative provider API reads.
    yookassa_ready = bool(
        _env("YOO_KASSA_SHOP_ID") and _env("YOO_KASSA_SECRET_KEY")
    )
    if not tbank_ready and not yookassa_ready:
        raise HTTPException(status_code=503, detail="Webhook provider authentication is not configured")
    return {
        "ok": True,
        "service": "billing-webhook",
        "supabase": "configured",
        "tbank": "configured" if tbank_ready else "disabled",
        "yookassa": "configured" if yookassa_ready else "disabled",
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


def _classify_yookassa_refund(refund, payment):
    """Do not deactivate a subscription unless the provider confirms a full cumulative refund."""
    refund_amount = refund.get("amount") if isinstance(refund, dict) else None
    payment_amount = payment.get("amount") if isinstance(payment, dict) else None
    refunded_amount = payment.get("refunded_amount") if isinstance(payment, dict) else None
    try:
        refund_value = Decimal(str(refund_amount.get("value")))
        paid_value = Decimal(str(payment_amount.get("value")))
    except (AttributeError, InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Refund amount verification failed")

    refund_currency = str(refund_amount.get("currency") or "").upper()
    payment_currency = str(payment_amount.get("currency") or "").upper()
    if (not refund_value.is_finite() or not paid_value.is_finite()
            or refund_value <= 0 or paid_value <= 0 or refund_value > paid_value):
        raise HTTPException(status_code=422, detail="Refund amount verification failed")
    if not payment_currency or refund_currency != payment_currency:
        raise HTTPException(status_code=422, detail="Refund currency verification failed")

    if isinstance(refunded_amount, dict) and refunded_amount.get("value") is not None:
        try:
            cumulative_value = Decimal(str(refunded_amount.get("value")))
        except (InvalidOperation, TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Refund total verification failed")
        cumulative_currency = str(refunded_amount.get("currency") or "").upper()
        if not cumulative_value.is_finite() or cumulative_value < refund_value or cumulative_value > paid_value:
            raise HTTPException(status_code=409, detail="Provider refund total is not yet consistent")
        if cumulative_currency != payment_currency:
            raise HTTPException(status_code=422, detail="Refund currency verification failed")
        return "refunded" if cumulative_value == paid_value else "partial_refunded"

    # Without a provider-reported cumulative total, only a single refund equal to the
    # original payment is sufficient evidence for a full refund.
    return "refunded" if refund_value == paid_value else "partial_refunded"


def _verify_tbank_payment_amount(payment, checkout):
    """Compare T-Bank's settled amount in kopecks against the server-side RUB checkout."""
    try:
        expected_rub = Decimal(str(checkout.get("expected_amount")))
        actual_kopecks = Decimal(str(payment.get("Amount")))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Checkout amount verification failed")
    expected_currency = str(checkout.get("expected_currency") or "").upper()
    if (not expected_rub.is_finite() or not actual_kopecks.is_finite()
            or expected_rub <= 0 or expected_rub * 100 != actual_kopecks):
        raise HTTPException(status_code=422, detail="Checkout amount verification failed")
    if expected_currency != "RUB":
        raise HTTPException(status_code=422, detail="Checkout currency verification failed")


def _checkout_by_payment(payment_id):
    url, _ = _supabase()
    rows = requests.get(
        f"{url}/rest/v1/billing_checkout_sessions",
        headers=_headers(),
        params={
            "select": "tenant_id,provider_order_id,provider_payment_id,plan,status,expected_amount,expected_currency",
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
    """Validate an optional configured Bearer layer.

    T-Bank notifications have their own signed Token. If a Bearer secret is
    configured for the T-Bank webhook API, a supplied Bearer header is checked;
    its absence is not rejected because the provider Token is independently
    verified below.
    """
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
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    return body


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
    # AUTHORIZED is an intermediate state. Never send it to the billing RPC:
    # this also protects deployments where the DB migration has not applied yet.
    if status == "AUTHORIZED":
        return PlainTextResponse("OK")
    if status == "CONFIRMED":
        _verify_tbank_payment_amount(state, checkout)
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

    return PlainTextResponse("OK")


@app.post("/webhooks/yookassa")
async def yookassa_payment_status(request: Request):
    # Standard YooKassa notifications do not include our custom Bearer header.
    # Validate it when supplied; state changes still require authoritative provider reads.
    _verify_webhook_secret(request, "YOOKASSA_WEBHOOK_SECRET")
    body = await _read_body(request)
    event = str(body.get("event") or "").strip().lower()
    obj = body.get("object")
    if not isinstance(obj, dict):
        raise HTTPException(status_code=400, detail="Invalid notification object")
    if not (event.startswith("payment.") or event.startswith("refund.")):
        raise HTTPException(status_code=400, detail="Unsupported notification event")

    is_refund = event.startswith("refund.")
    refund_id = ""
    if is_refund:
        refund_id = str(obj.get("id") or "").strip()
        payment_id = str(obj.get("payment_id") or "").strip()
        if not refund_id or not payment_id:
            raise HTTPException(status_code=400, detail="Refund and payment ids are required")
        refund = get_refund(refund_id)
        if str(refund.get("id") or refund_id) != refund_id:
            raise HTTPException(status_code=400, detail="Refund id mismatch")
        if str(refund.get("payment_id") or "") != payment_id:
            raise HTTPException(status_code=400, detail="Refund/payment mismatch")
        refund_status = str(refund.get("status") or "").lower()
        payment = get_payment(payment_id)
        if str(payment.get("id") or payment_id) != payment_id:
            raise HTTPException(status_code=400, detail="Payment id mismatch")
        provider_status = str(payment.get("status") or "").lower()
        if refund_status == "succeeded":
            status = _classify_yookassa_refund(refund, payment)
        elif refund_status == "canceled":
            status = "refund_canceled"
        else:
            status = "refund_pending"
    else:
        payment_id = str(obj.get("id") or "").strip()
        if not payment_id:
            raise HTTPException(status_code=400, detail="Payment id is required")
        payment = get_payment(payment_id)
        if str(payment.get("id") or payment_id) != payment_id:
            raise HTTPException(status_code=400, detail="Payment id mismatch")
        provider_status = str(payment.get("status") or "").lower()
        status = provider_status

    checkout = _checkout_by_provider_payment("yookassa", payment_id)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    if not is_refund and provider_status in ("succeeded", "confirmed"):
        _verify_yookassa_payment_amount(payment, checkout)

    plan = str(checkout.get("plan") or "").lower()
    tenant = str(checkout.get("tenant_id") or "")
    if plan not in ("starter", "pro", "business") or not tenant:
        raise HTTPException(status_code=422, detail="Invalid checkout session")

    payment_method = payment.get("payment_method") or {}
    payment_method_id = payment_method.get("id") if payment_method.get("saved") else None
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
        raise HTTPException(status_code=502, detail="Billing state transition failed") from exc

    return {
        "ok": True,
        "event": event,
        "payment_id": payment_id,
        "status": status,
        "provider_status": provider_status,
        "plan": plan,
        "duplicate": bool((result or {}).get("duplicate")),
    }
