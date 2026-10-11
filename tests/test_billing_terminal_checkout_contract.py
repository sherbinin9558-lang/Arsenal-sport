from pathlib import Path


def test_delayed_success_cannot_reactivate_terminal_checkout():
    migration = Path(
        "supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql"
    ).read_text(encoding="utf-8")
    assert "lower(coalesce(checkout.status,''))" in migration
    assert "'refunded','reversed','canceled','cancelled','rejected','deadline_expired'" in migration
    assert "'ignored', true, 'reason', 'checkout_terminal'" in migration
    guard = migration.index("-- Do not let a delayed success notification")
    activation = migration.index("perform public.activate_paid_subscription(")
    assert guard < activation
