import pytest
import billing
import saas_billing


def test_checkout_does_not_request_saved_payment_method(monkeypatch):
    monkeypatch.setattr(billing, "configured", lambda: True)
    monkeypatch.setattr(billing, "plan_price", lambda _plan: 100)
    monkeypatch.setattr(billing, "SHOP_ID", "test-shop")
    monkeypatch.setattr(billing, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(billing, "PUBLIC_URL", "https://app.example.invalid")
    monkeypatch.setattr(billing, "_cfg", lambda name, default="": {
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "SUPABASE_URL": "https://example.supabase.co",
    }.get(name, default))
    captured = {}

    class Response:
        ok = True
        def json(self):
            return {"id": "payment-test", "confirmation": {"confirmation_url": "https://pay.example.invalid"}}

    def fake_post(url, **kwargs):
        if kwargs.get("auth") == ("test-shop", "test-secret"):
            captured.update(kwargs["json"])
            return Response()
        return Response()

    monkeypatch.setattr(billing.requests, "post", fake_post)
    monkeypatch.setattr(billing, "_save_checkout", lambda *args: None)
    billing.create_checkout("pro", "tenant-test")
    assert captured.get("save_payment_method", False) is False


def test_auto_renew_cannot_be_enabled_until_recurring_charges_exist(monkeypatch):
    called = []
    monkeypatch.setattr(saas_billing.requests, "patch", lambda *args, **kwargs: called.append(args))
    with pytest.raises(RuntimeError, match="автоматические повторные списания не реализованы"):
        saas_billing.set_auto_renew(
            True,
            tenant_id=lambda: "tenant-test",
            saas_is_enabled=True,
            current_role=lambda: "owner",
            service_key="test-service-key",
            supabase_url="https://example.supabase.co",
        )
    assert called == []


def test_auto_renew_cannot_be_enabled_in_demo_mode():
    with pytest.raises(RuntimeError, match="автоматические повторные списания не реализованы"):
        saas_billing.set_auto_renew(
            True,
            tenant_id=lambda: "demo-tenant",
            saas_is_enabled=False,
            current_role=lambda: "owner",
            service_key="",
            supabase_url="",
        )
