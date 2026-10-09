"""Network-free payment lifecycle test using an in-memory YooKassa-compatible fake."""
import asyncio
from unittest.mock import patch

import billing
import tbank_webhook


class FakeResponse:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self.ok = ok
        self.text = "fake response"

    def json(self):
        return self._payload


class FakeYooKassa:
    """A test-only provider; unknown endpoints fail instead of reaching the network."""

    base_url = "https://api.yookassa.com/v3/payments"

    def __init__(self):
        self.payments = {}
        self.checkouts = []
        self.sequence = 0
        self.rpc_events = []
        self.seen_event_keys = set()

    def post(self, url, **kwargs):
        if kwargs.get("auth") == ("test-shop", "test-secret"):
            self.sequence += 1
            payment_id = f"fake-payment-{self.sequence}"
            checkout_id = kwargs["headers"]["Idempotence-Key"]
            payment = {
                "id": payment_id,
                "status": "pending",
                "amount": kwargs["json"]["amount"],
                "confirmation": {
                    "type": "redirect",
                    "confirmation_url": f"https://fake-payments.invalid/checkout/{checkout_id}",
                },
            }
            self.payments[payment_id] = payment
            return FakeResponse(payment)
        if url.endswith("/rest/v1/billing_checkout_sessions"):
            self.checkouts.append(dict(kwargs["json"]))
            return FakeResponse([])
        if url.endswith("/rest/v1/rpc/process_billing_payment_event"):
            rpc_payload = dict(kwargs["json"])
            event_key = rpc_payload["p_event_key"]
            duplicate = event_key in self.seen_event_keys
            self.seen_event_keys.add(event_key)
            self.rpc_events.append(rpc_payload)
            return FakeResponse({"ok": True, "duplicate": duplicate})
        raise AssertionError(f"Unexpected outbound POST in fake-provider test: {url}")

    def get(self, url, **kwargs):
        if kwargs.get("auth") == ("test-shop", "test-secret"):
            payment_id = url.rsplit("/", 1)[-1]
            if payment_id not in self.payments:
                return FakeResponse({"error": "not found"}, ok=False)
            return FakeResponse(self.payments[payment_id])
        if url.endswith("/rest/v1/billing_checkout_sessions"):
            checkout_id = kwargs["params"]["provider_order_id"].removeprefix("eq.")
            rows = [row for row in self.checkouts if row["provider_order_id"] == checkout_id]
            return FakeResponse([{
                "tenant_id": row["tenant_id"],
                "provider_payment_id": row["provider_payment_id"],
                "plan": row["plan"],
                "status": row["status"],
            } for row in rows])
        raise AssertionError(f"Unexpected outbound GET in fake-provider test: {url}")


def test_checkout_then_verified_webhook_is_network_free(monkeypatch):
    fake = FakeYooKassa()
    monkeypatch.setattr(billing, "SHOP_ID", "test-shop")
    monkeypatch.setattr(billing, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(billing, "PUBLIC_URL", "https://app.example.invalid")
    monkeypatch.setattr(billing, "configured", lambda: True)
    monkeypatch.setattr(billing, "plan_price", lambda plan: 125.0 if plan == "pro" else 0.0)
    monkeypatch.setattr(billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "fake-service-key",
        "SUPABASE_URL": "https://fake-project.supabase.co",
    }.get(name, default))
    monkeypatch.setattr(billing.requests, "post", fake.post)
    monkeypatch.setattr(billing.requests, "get", fake.get)

    checkout = billing.create_checkout("pro", "tenant-alpha")
    assert checkout["id"] == "fake-payment-1"
    assert checkout["status"] == "pending"
    assert len(fake.checkouts) == 1
    session = fake.checkouts[0]
    assert session["tenant_id"] == "tenant-alpha"
    assert session["plan"] == "pro"
    assert session["provider_payment_id"] == "fake-payment-1"

    # Simulate the provider's server-side state changing before it sends an event.
    fake.payments["fake-payment-1"]["status"] = "succeeded"
    monkeypatch.setattr(tbank_webhook, "_checkout_by_provider_payment",
                        lambda provider, payment_id: {
                            "tenant_id": session["tenant_id"],
                            "plan": session["plan"],
                        })
    # Keep the production _process_billing_event implementation active. The
    # fake intercepts its Supabase RPC request and models duplicate-key behavior;
    # this is not a substitute for real database/RPC tests.
    monkeypatch.setenv("YOOKASSA_WEBHOOK_SECRET", "fake-webhook-secret")

    class Request:
        headers = {"authorization": "Bearer fake-webhook-secret"}

    async def read_body(_request):
        return {"event": "payment.succeeded", "object": {"id": "fake-payment-1"}}

    monkeypatch.setattr(tbank_webhook, "_read_body", read_body)
    response = asyncio.run(tbank_webhook.yookassa_payment_status(Request()))
    duplicate_response = asyncio.run(tbank_webhook.yookassa_payment_status(Request()))

    assert response["ok"] is True
    assert response["status"] == "succeeded"
    assert duplicate_response["duplicate"] is True
    assert len(fake.rpc_events) == 2
    first, second = fake.rpc_events
    assert first["p_provider"] == "yookassa"
    assert first["p_provider_payment_id"] == "fake-payment-1"
    assert first["p_tenant_id"] == "tenant-alpha"
    assert first["p_plan"] == "pro"
    assert first["p_status"] == "succeeded"
    assert first["p_event_key"] == second["p_event_key"]


def test_invalid_plan_never_contacts_fake_or_live_provider(monkeypatch):
    fake = FakeYooKassa()
    monkeypatch.setattr(billing.requests, "post", fake.post)
    with patch.object(billing, "plan_price", side_effect=ValueError("Недопустимый тариф.")):
        try:
            billing.create_checkout("unknown", "tenant-alpha")
        except ValueError as exc:
            assert "Недопустимый тариф" in str(exc)
        else:
            raise AssertionError("invalid plan must be rejected")
    assert fake.payments == {}
    assert fake.checkouts == []
