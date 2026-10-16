import saas_billing


def test_plan_catalog_has_supported_plans():
    catalog = saas_billing.plan_catalog()
    assert set(catalog) == {"starter", "pro", "business"}
    assert catalog["business"]["users"] == 50


def test_request_plan_change_uses_supplied_state():
    state = {}
    assert saas_billing.request_plan_change("pro", state=state) is True
    assert state["requested_plan"] == "pro"


def test_request_plan_change_rejects_unknown_plan():
    try:
        saas_billing.request_plan_change("enterprise", state={})
    except ValueError as exc:
        assert "Недопустимый тариф" in str(exc)
    else:
        raise AssertionError("unknown plan must be rejected")


def test_subscription_snapshot_is_safe_without_saas():
    state = {}
    result = saas_billing.subscription_snapshot(
        token=None,
        tenant_id=lambda: "tenant-1",
        saas_is_enabled=False,
        subscription_loader=lambda *_: (_ for _ in ()).throw(AssertionError("must not load")),
        tenant_plan=lambda: "trial",
    )
    assert result["plan"] == "trial"
    assert result["status"] == "trialing"
    assert result["auto_renew"] is False


def test_activate_paid_subscription_requires_service_key():
    try:
        saas_billing.activate_paid_subscription(
            "pro",
            "payment-1",
            service_key="",
            supabase_url="https://example.supabase.co",
            saas_is_enabled=True,
            tenant_id=lambda: "tenant-1",
        )
    except RuntimeError as exc:
        assert "SUPABASE_SERVICE_ROLE_KEY" in str(exc)
    else:
        raise AssertionError("missing service key must be rejected")


def test_activate_paid_subscription_does_not_expose_supabase_error(monkeypatch):
    class Response:
        ok = False
        text = "secret database schema and internal diagnostic"

    monkeypatch.setattr(saas_billing.requests, "post", lambda *args, **kwargs: Response())
    try:
        saas_billing.activate_paid_subscription(
            "pro", "payment-1", service_key="service-key",
            supabase_url="https://example.supabase.co", saas_is_enabled=True,
            tenant_id=lambda: "tenant-1",
        )
    except RuntimeError as exc:
        assert "secret database schema" not in str(exc)
        assert "платёжной базе" in str(exc)
    else:
        raise AssertionError("failed activation must raise a sanitized error")


def test_set_auto_renew_does_not_expose_supabase_error(monkeypatch):
    class Response:
        ok = False
        text = "secret database schema and internal diagnostic"

    monkeypatch.setattr(saas_billing.requests, "patch", lambda *args, **kwargs: Response())
    try:
        saas_billing.set_auto_renew(
            True, tenant_id=lambda: "tenant-1", saas_is_enabled=True,
            current_role=lambda: "owner", service_key="service-key",
            supabase_url="https://example.supabase.co",
        )
    except RuntimeError as exc:
        assert "secret database schema" not in str(exc)
        assert "платёжной базе" in str(exc)
    else:
        raise AssertionError("failed renewal update must raise a sanitized error")
