"""Regression tests for recovery when YooKassa creates a payment but checkout persistence fails."""
from fastapi import HTTPException
import pytest

import tbank_webhook


def settled_payment(**overrides):
    payment = {
        "id": "pay-recovery-123",
        "status": "succeeded",
        "amount": {"value": "990.00", "currency": "RUB"},
        "metadata": {
            "checkout_id": "checkout-local-123",
            "tenant_id": "tenant-test-123",
            "plan": "pro",
            "expected_amount": "990.00",
            "expected_currency": "RUB",
        },
    }
    payment.update(overrides)
    return payment


def test_recovery_persists_verified_settled_payment(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        tbank_webhook,
        "_save_checkout",
        lambda tenant, checkout_id, payment_id, plan, amount, currency:
            saved.update(tenant=tenant, checkout_id=checkout_id, payment_id=payment_id,
                         plan=plan, amount=amount, currency=currency),
    )
    monkeypatch.setattr(
        tbank_webhook,
        "_checkout_by_provider_payment",
        lambda provider, payment_id: {
            "tenant_id": saved["tenant"], "plan": saved["plan"],
            "provider_order_id": saved["checkout_id"],
            "provider_payment_id": payment_id,
            "expected_amount": saved["amount"], "expected_currency": saved["currency"],
        } if saved else None,
    )

    recovered = tbank_webhook._recover_checkout_from_provider(settled_payment())

    assert recovered["provider_payment_id"] == "pay-recovery-123"
    assert saved == {
        "tenant": "tenant-test-123",
        "checkout_id": "checkout-local-123",
        "payment_id": "pay-recovery-123",
        "plan": "pro",
        "amount": "990.00",
        "currency": "RUB",
    }


def test_recovery_returns_existing_row_after_concurrent_save(monkeypatch):
    existing = {
        "tenant_id": "tenant-test-123", "plan": "pro",
        "provider_order_id": "checkout-local-123", "provider_payment_id": "pay-recovery-123",
        "expected_amount": "990.00", "expected_currency": "RUB",
    }
    monkeypatch.setattr(tbank_webhook, "_save_checkout", lambda *args: (_ for _ in ()).throw(RuntimeError("duplicate insert")))
    monkeypatch.setattr(tbank_webhook, "_checkout_by_provider_payment", lambda provider, payment_id: existing)

    assert tbank_webhook._recover_checkout_from_provider(settled_payment()) == existing


def test_recovery_fails_retryably_if_storage_failed_and_row_is_missing(monkeypatch):
    monkeypatch.setattr(tbank_webhook, "_save_checkout", lambda *args: (_ for _ in ()).throw(RuntimeError("storage unavailable")))
    monkeypatch.setattr(tbank_webhook, "_checkout_by_provider_payment", lambda provider, payment_id: None)

    with pytest.raises(HTTPException) as exc:
        tbank_webhook._recover_checkout_from_provider(settled_payment())

    assert exc.value.status_code == 503
    assert exc.value.detail == "Checkout recovery is temporarily unavailable"


def test_recovery_rejects_amount_mismatch_before_persisting(monkeypatch):
    persisted = []
    monkeypatch.setattr(tbank_webhook, "_save_checkout", lambda *args: persisted.append(args))

    payment = settled_payment(amount={"value": "9.90", "currency": "RUB"})
    with pytest.raises(HTTPException) as exc:
        tbank_webhook._recover_checkout_from_provider(payment)

    assert exc.value.status_code == 422
    assert exc.value.detail == "Checkout amount verification failed"
    assert persisted == []


@pytest.mark.parametrize("status", ["pending", "waiting_for_capture", "canceled"])
def test_recovery_rejects_unsettled_provider_payment(monkeypatch, status):
    monkeypatch.setattr(tbank_webhook, "_save_checkout", lambda *args: pytest.fail("must not persist an unsettled payment"))

    with pytest.raises(HTTPException) as exc:
        tbank_webhook._recover_checkout_from_provider(settled_payment(status=status))

    assert exc.value.status_code == 404


def test_recovery_rejects_missing_or_invalid_metadata_before_persisting(monkeypatch):
    monkeypatch.setattr(tbank_webhook, "_save_checkout", lambda *args: pytest.fail("must not persist invalid metadata"))

    payment = settled_payment(metadata={"tenant_id": "tenant-test-123", "plan": "admin"})
    with pytest.raises(HTTPException) as exc:
        tbank_webhook._recover_checkout_from_provider(payment)

    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "tenant-other"),
        ("plan", "business"),
        ("provider_order_id", "checkout-other"),
        ("provider_payment_id", "pay-other"),
        ("expected_amount", "9.90"),
        ("expected_currency", "EUR"),
    ],
)
def test_recovery_rejects_mismatched_existing_row_after_concurrent_save(monkeypatch, field, value):
    existing = {
        "tenant_id": "tenant-test-123",
        "plan": "pro",
        "provider_order_id": "checkout-local-123",
        "provider_payment_id": "pay-recovery-123",
        "expected_amount": "990.00",
        "expected_currency": "RUB",
    }
    existing[field] = value
    monkeypatch.setattr(
        tbank_webhook, "_save_checkout",
        lambda *args: (_ for _ in ()).throw(RuntimeError("concurrent insert")),
    )
    monkeypatch.setattr(tbank_webhook, "_checkout_by_provider_payment", lambda provider, payment_id: existing)

    with pytest.raises(HTTPException) as exc:
        tbank_webhook._recover_checkout_from_provider(settled_payment())

    assert exc.value.status_code == 409
    assert exc.value.detail == "Recovered checkout does not match payment"
