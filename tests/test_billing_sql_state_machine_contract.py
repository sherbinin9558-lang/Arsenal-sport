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
