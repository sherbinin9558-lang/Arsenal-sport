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
