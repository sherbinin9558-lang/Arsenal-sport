from pathlib import Path


def test_delayed_success_cannot_reactivate_terminal_checkout():
    migration = Path("supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql").read_text(encoding="utf-8")
    assert "lower(coalesce(checkout.status,''))" in migration
    assert "'refunded','reversed','canceled','cancelled','rejected','deadline_expired'" in migration
    assert "'ignored', true, 'reason', 'checkout_terminal'" in migration
    assert migration.index("-- A terminal checkout is immutable:") < migration.index("perform public.activate_paid_subscription(")


def test_authorized_status_never_activates_subscription():
    migration = Path("supabase/migrations/20261009170000_require_captured_payment_for_activation.sql").read_text(encoding="utf-8")
    assert "if normalized_status in ('succeeded','confirmed') then" in migration
    assert "if normalized_status in ('succeeded','confirmed','authorized') then" not in migration


def test_checkout_amount_columns_are_migrated_before_terminal_guard():
    migration = Path("supabase/migrations/20261009190000_billing_checkout_amount_validation.sql").read_text(encoding="utf-8")
    assert "add column if not exists expected_amount numeric(12,2)" in migration
    assert "add column if not exists expected_currency text" in migration
