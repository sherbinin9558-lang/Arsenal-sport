"""Guard the billing SQL contract against premature activation on AUTHORIZED."""
from pathlib import Path


def test_authorized_payment_does_not_activate_subscription():
    migration = Path(
        'supabase/migrations/20261009170000_require_captured_payment_for_activation.sql'
    ).read_text(encoding='utf-8')
    assert "if normalized_status in ('succeeded','confirmed') then" in migration
    assert "if normalized_status in ('succeeded','confirmed','authorized') then" not in migration
    assert "perform public.activate_paid_subscription(" in migration


def test_refund_and_reversal_lifecycle_remains_present():
    migration = Path(
        'supabase/migrations/20261009170000_require_captured_payment_for_activation.sql'
    ).read_text(encoding='utf-8')
    assert "'refunded','reversed','canceled','cancelled','rejected','deadline_expired'" in migration
    assert "public.deactivate_paid_subscription" in migration

def test_browser_payment_return_never_activates_subscription():
    app = Path("app.py").read_text(encoding="utf-8")
    start = app.index("# Browser return is informational only.")
    end = app.index("\n\nwith st.sidebar:", start)
    return_flow = app[start:end]
    assert "activate_paid_subscription(" not in return_flow
    assert 'status == "AUTHORIZED"' in return_flow
    assert "Тариф пока не активирован" in return_flow
    assert "проверки суммы, валюты и платёжного уведомления" in return_flow

def test_checkout_amount_migration_adds_server_expected_amount_and_currency():
    migration = Path(
        "supabase/migrations/20261009190000_billing_checkout_amount_validation.sql"
    ).read_text(encoding="utf-8")
    assert "add column if not exists expected_amount numeric(12,2)" in migration
    assert "add column if not exists expected_currency text" in migration
    assert "Expected amount from the server-created checkout" in migration
    assert "Expected ISO currency from the server-created checkout" in migration


def test_yookassa_webhook_fails_closed_when_expected_amount_or_currency_missing():
    source = Path("tbank_webhook.py").read_text(encoding="utf-8")
    start = source.index("def _verify_yookassa_payment_amount(")
    end = source.index("\n\ndef ", start + 5)
    verifier = source[start:end]
    assert "expected_amount" in verifier
    assert "expected_currency" in verifier
    assert "Checkout amount verification failed" in verifier
    assert "Checkout currency verification failed" in verifier
    assert "status_code=422" in verifier

def test_duplicate_processed_webhook_event_is_idempotent():
    migration = Path(
        "supabase/migrations/20261009170000_require_captured_payment_for_activation.sql"
    ).read_text(encoding="utf-8")
    assert "on conflict (provider, event_key) do nothing" in migration
    assert "if event_status = 'processed' then" in migration
    assert "jsonb_build_object('ok', true, 'duplicate', true, 'status', 'processed')" in migration


def test_billing_state_transition_checks_tenant_and_plan_before_activation():
    migration = Path(
        "supabase/migrations/20261009170000_require_captured_payment_for_activation.sql"
    ).read_text(encoding="utf-8")
    assert "and tenant_id = p_tenant_id" in migration
    assert "if checkout.plan <> p_plan then" in migration
    assert "raise exception 'CHECKOUT_NOT_FOUND'" in migration
    assert "raise exception 'PLAN_MISMATCH'" in migration
