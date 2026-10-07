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
