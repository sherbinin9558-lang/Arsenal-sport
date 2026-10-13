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



def test_browser_return_never_activates_subscription():
    app = Path("app.py").read_text(encoding="utf-8")
    start = app.index("# Browser return is informational only.")
    end = app.index("\n\nwith st.sidebar:", start)
    browser_return = app[start:end]
    assert "activate_paid_subscription(" not in browser_return
    assert 'status == "AUTHORIZED"' in browser_return
    assert "Тариф пока не активирован" in browser_return


def test_checkout_amount_migration_adds_expected_amount_and_currency():
    migration = Path(
        "supabase/migrations/20261009190000_billing_checkout_amount_validation.sql"
    ).read_text(encoding="utf-8")
    assert "add column if not exists expected_amount numeric(12,2)" in migration
    assert "add column if not exists expected_currency text" in migration


def test_yookassa_amount_checker_fails_closed_when_values_are_missing():
    source = Path("tbank_webhook.py").read_text(encoding="utf-8")
    start = source.index("def _verify_yookassa_payment_amount(")
    end = source.index("\n\ndef ", start + 5)
    verifier = source[start:end]
    assert "expected_amount" in verifier
    assert "expected_currency" in verifier
    assert "status_code=422" in verifier
