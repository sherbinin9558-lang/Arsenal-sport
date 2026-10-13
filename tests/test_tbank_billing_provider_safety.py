"""T-Bank billing safety regression tests; no real provider calls are made."""
from unittest.mock import patch

import pytest
import billing
import tbank_billing


class FakeResponse:
    def __init__(self, payload=None, ok=True, text="PRIVATE_PROVIDER_DIAGNOSTIC"):
        self.payload = payload if payload is not None else {}
        self.ok = ok
        self.text = text

    def json(self):
        return self.payload


@pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "0", "-10", "invalid", ""])
def test_yookassa_plan_price_rejects_invalid_values(monkeypatch, raw):
    monkeypatch.setattr(billing, "_cfg", lambda *_args, **_kwargs: raw)
    assert billing.plan_price("starter") == 0.0


@pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "0", "-10", "invalid", ""])
def test_tbank_plan_price_rejects_invalid_values(monkeypatch, raw):
    monkeypatch.setattr(tbank_billing, "_cfg", lambda *_args, **_kwargs: raw)
    assert tbank_billing.plan_price("starter") == 0.0


def test_tbank_plan_price_rejects_unknown_plan():
    with pytest.raises(ValueError, match="Недопустимый тариф"):
        tbank_billing.plan_price("unknown")


def test_tbank_checkout_error_does_not_expose_provider_body(monkeypatch):
    monkeypatch.setattr(tbank_billing, "configured", lambda: True)
    monkeypatch.setattr(tbank_billing, "plan_price", lambda _plan: 100.0)
    monkeypatch.setattr(tbank_billing.requests, "post", lambda *_args, **_kwargs: FakeResponse(
        {"Success": False, "Message": "PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"},
        text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value",
    ))
    with pytest.raises(RuntimeError) as exc:
        tbank_billing.create_checkout("starter", "tenant-test")
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in str(exc.value)
    assert "private-secret-value" not in str(exc.value)


def test_tbank_payment_state_error_does_not_expose_provider_body(monkeypatch):
    monkeypatch.setattr(tbank_billing, "configured", lambda: True)
    monkeypatch.setattr(tbank_billing.requests, "post", lambda *_args, **_kwargs: FakeResponse(
        {"Success": False, "Message": "PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value"},
        text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value",
    ))
    with pytest.raises(RuntimeError) as exc:
        tbank_billing.get_state("payment-test")
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in str(exc.value)
    assert "private-secret-value" not in str(exc.value)


def test_tbank_storage_error_does_not_expose_database_body(monkeypatch):
    monkeypatch.setattr(tbank_billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "private-secret-value",
        "SUPABASE_URL": "https://example.supabase.co",
    }.get(name, default))
    monkeypatch.setattr(tbank_billing.requests, "post", lambda *_args, **_kwargs: FakeResponse(
        {}, ok=False, text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value",
    ))
    with pytest.raises(RuntimeError) as exc:
        tbank_billing._save_checkout("tenant-test", "order-test", "payment-test", "starter")
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in str(exc.value)
    assert "private-secret-value" not in str(exc.value)


def test_tbank_checkout_lookup_error_does_not_expose_database_body(monkeypatch):
    monkeypatch.setattr(tbank_billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "private-secret-value",
        "SUPABASE_URL": "https://example.supabase.co",
    }.get(name, default))
    monkeypatch.setattr(tbank_billing.requests, "get", lambda *_args, **_kwargs: FakeResponse(
        {}, ok=False, text="PRIVATE_PROVIDER_DIAGNOSTIC private-secret-value",
    ))
    with pytest.raises(RuntimeError) as exc:
        tbank_billing.get_checkout_by_order("order-test", "tenant-test")
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in str(exc.value)
    assert "private-secret-value" not in str(exc.value)
