"""YooKassa webhooks must verify authoritative provider state without assuming custom headers."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import billing
import tbank_webhook


def invoke_webhook(monkeypatch, payload, headers=None):
    request = SimpleNamespace(headers=headers or {})
    async def read_body(_request):
        return payload
    monkeypatch.setattr(tbank_webhook, '_read_body', read_body)
    return asyncio.run(tbank_webhook.yookassa_payment_status(request))


def test_payment_notification_without_bearer_uses_authoritative_provider_status(monkeypatch):
    monkeypatch.setenv('YOOKASSA_WEBHOOK_SECRET', 'optional-extra-secret')
    monkeypatch.setattr(tbank_webhook, 'get_payment', lambda _payment_id: {'id': 'pay-1', 'status': 'succeeded'})
    monkeypatch.setattr(tbank_webhook, '_checkout_by_provider_payment', lambda provider, payment_id: {'tenant_id': 'tenant-a', 'plan': 'pro'})
    captured = {}
    monkeypatch.setattr(tbank_webhook, '_process_billing_event', lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {'duplicate': False})
    result = invoke_webhook(monkeypatch, {'event': 'payment.succeeded', 'object': {'id': 'pay-1', 'status': 'canceled'}})
    assert result['status'] == 'succeeded'
    assert captured['args'][3] == 'succeeded'
    assert captured['args'][4] == 'tenant-a'


def test_wrong_optional_bearer_is_rejected(monkeypatch):
    monkeypatch.setenv('YOOKASSA_WEBHOOK_SECRET', 'expected-secret')
    with pytest.raises(Exception) as exc:
        invoke_webhook(monkeypatch, {'event': 'payment.succeeded', 'object': {'id': 'pay-1'}}, {'authorization': 'Bearer wrong-secret'})
    assert getattr(exc.value, 'status_code', None) == 401


def test_refund_notification_fetches_refund_and_uses_refund_id_for_idempotency(monkeypatch):
    monkeypatch.setenv('YOOKASSA_WEBHOOK_SECRET', 'optional-extra-secret')
    refund_fetch = Mock(return_value={'id': 'refund-77', 'payment_id': 'pay-1', 'status': 'succeeded'})
    monkeypatch.setattr(tbank_webhook, 'get_refund', refund_fetch)
    monkeypatch.setattr(tbank_webhook, 'get_payment', lambda _payment_id: {'id': 'pay-1', 'status': 'succeeded'})
    monkeypatch.setattr(tbank_webhook, '_checkout_by_provider_payment', lambda provider, payment_id: {'tenant_id': 'tenant-a', 'plan': 'pro'})
    captured = {}
    monkeypatch.setattr(tbank_webhook, '_process_billing_event', lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {'duplicate': False})
    result = invoke_webhook(monkeypatch, {'event': 'refund.succeeded', 'object': {'id': 'refund-77', 'payment_id': 'pay-1'}})
    refund_fetch.assert_called_once_with('refund-77')
    assert result['status'] == 'refunded'
    assert captured['args'][1] == 'yookassa:refund.succeeded:refund-77:refunded'
    assert captured['args'][2] == 'pay-1'


def test_refund_status_from_notification_is_not_trusted(monkeypatch):
    monkeypatch.setenv('YOOKASSA_WEBHOOK_SECRET', '')
    monkeypatch.setattr(tbank_webhook, 'get_refund', lambda _refund_id: {'id': 'refund-77', 'payment_id': 'pay-1', 'status': 'pending'})
    monkeypatch.setattr(tbank_webhook, 'get_payment', lambda _payment_id: {'id': 'pay-1', 'status': 'succeeded'})
    monkeypatch.setattr(tbank_webhook, '_checkout_by_provider_payment', lambda provider, payment_id: {'tenant_id': 'tenant-a', 'plan': 'pro'})
    captured = {}
    monkeypatch.setattr(tbank_webhook, '_process_billing_event', lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {'duplicate': False})
    result = invoke_webhook(monkeypatch, {'event': 'refund.succeeded', 'object': {'id': 'refund-77', 'payment_id': 'pay-1', 'status': 'succeeded'}})
    assert result['status'] == 'refund_pending'
    assert captured['args'][3] == 'refund_pending'


def test_refund_for_another_payment_is_rejected(monkeypatch):
    monkeypatch.setenv('YOOKASSA_WEBHOOK_SECRET', '')
    monkeypatch.setattr(tbank_webhook, 'get_refund', lambda _refund_id: {'id': 'refund-77', 'payment_id': 'different-payment', 'status': 'succeeded'})
    process = Mock()
    monkeypatch.setattr(tbank_webhook, '_process_billing_event', process)
    with pytest.raises(Exception) as exc:
        invoke_webhook(monkeypatch, {'event': 'refund.succeeded', 'object': {'id': 'refund-77', 'payment_id': 'pay-1'}})
    assert getattr(exc.value, 'status_code', None) == 400
    process.assert_not_called()


def test_get_refund_escapes_id_and_sanitizes_provider_errors(monkeypatch):
    monkeypatch.setattr(billing, 'configured', lambda: True)
    monkeypatch.setattr(billing, 'SHOP_ID', 'test-shop')
    monkeypatch.setattr(billing, 'SECRET_KEY', 'test-secret')
    response = SimpleNamespace(ok=False, text='PRIVATE_PROVIDER_SECRET', json=lambda: {'description': 'PRIVATE_PROVIDER_SECRET'})
    call = Mock(return_value=response)
    monkeypatch.setattr(billing.requests, 'get', call)
    with pytest.raises(RuntimeError) as exc:
        billing.get_refund('refund/with?unsafe=query')
    assert 'PRIVATE_PROVIDER_SECRET' not in str(exc.value)
    assert '/v3/refunds/refund%2Fwith%3Funsafe%3Dquery' in call.call_args.args[0]
