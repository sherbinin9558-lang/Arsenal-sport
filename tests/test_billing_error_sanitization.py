"""Billing errors must be actionable without leaking provider/database response bodies."""
import pytest
from unittest.mock import Mock

import billing
import saas_billing


class Response:
    def __init__(self, payload=None, ok=False, text="PRIVATE_PROVIDER_DIAGNOSTIC"):
        self._payload = payload if payload is not None else {}
        self.ok = ok
        self.text = text

    def json(self):
        return self._payload


def assert_sanitized(call):
    with pytest.raises(RuntimeError) as exc:
        call()
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in str(exc.value)
    assert "private-secret-value" not in str(exc.value)


def test_create_checkout_does_not_expose_provider_error(monkeypatch):
    monkeypatch.setattr(billing, "configured", lambda: True)
    monkeypatch.setattr(billing, "plan_price", lambda _plan: 100)
    monkeypatch.setattr(billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "private-secret-value",
        "SUPABASE_URL": "https://example.supabase.co",
    }.get(name, default))
    response = Response({"description": "PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"})
    monkeypatch.setattr(billing.requests, "post", Mock(return_value=response))

    assert_sanitized(lambda: billing.create_checkout("pro", "tenant-test"))


def test_get_payment_does_not_expose_provider_error(monkeypatch):
    monkeypatch.setattr(billing, "configured", lambda: True)
    monkeypatch.setattr(billing.requests, "get", Mock(return_value=Response(
        {"description": "PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"}
    )))

    assert_sanitized(lambda: billing.get_payment("payment-test"))


@pytest.mark.parametrize("operation", ["save", "lookup"])
def test_checkout_storage_errors_do_not_expose_database_body(monkeypatch, operation):
    monkeypatch.setattr(billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "private-secret-value",
        "SUPABASE_URL": "https://example.supabase.co",
    }.get(name, default))
    monkeypatch.setattr(billing.requests, "post" if operation == "save" else "get",
                        Mock(return_value=Response(text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value")))

    call = (lambda: billing._save_checkout("tenant-test", "checkout-test", "payment-test", "pro")) if operation == "save" else (
        lambda: billing.get_checkout_by_order("checkout-test")
    )
    assert_sanitized(call)


def test_activate_subscription_does_not_expose_database_body(monkeypatch):
    monkeypatch.setattr(saas_billing.requests, "post", Mock(return_value=Response(
        text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"
    )))

    assert_sanitized(lambda: saas_billing.activate_paid_subscription(
        "pro", "payment-test", service_key="private-secret-value",
        supabase_url="https://example.supabase.co", saas_is_enabled=True,
        tenant_id=lambda: "tenant-test",
    ))


def test_auto_renew_does_not_expose_database_body(monkeypatch):
    monkeypatch.setattr(saas_billing.requests, "patch", Mock(return_value=Response(
        text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"
    )))

    assert_sanitized(lambda: saas_billing.set_auto_renew(
        False, tenant_id=lambda: "tenant-test", saas_is_enabled=True,
        current_role=lambda: "owner", service_key="private-secret-value",
        supabase_url="https://example.supabase.co",
    ))
