from pathlib import Path


def test_delayed_success_cannot_reactivate_terminal_checkout():
    migration = Path(
        "supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql"
    ).read_text(encoding="utf-8")
    assert "lower(coalesce(checkout.status,''))" in migration
    assert "'refunded','reversed','canceled','cancelled','rejected','deadline_expired'" in migration
    assert "'ignored', true, 'reason', 'checkout_terminal'" in migration
    guard = migration.index("-- A terminal checkout is immutable:")
    activation = migration.index("perform public.activate_paid_subscription(")
    assert guard < activation

def test_terminal_checkout_guard_applies_to_all_later_event_statuses():
    migration = Path(
        "supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql"
    ).read_text(encoding="utf-8")
    guard_start = migration.index("-- A terminal checkout is immutable:")
    guard_end = migration.index("  if normalized_status in ('succeeded','confirmed') then", guard_start)
    guard = migration[guard_start:guard_end]
    assert "if lower(coalesce(checkout.status,'')) in" in guard
    assert "normalized_status in ('succeeded','confirmed')" not in guard
    assert "'refund_pending'" not in guard
    assert "'refund_canceled'" not in guard
    assert "'ignored', true, 'reason', 'checkout_terminal'" in guard

def test_all_terminal_checkout_states_are_guarded_before_event_handling():
    migration = Path(
        "supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql"
    ).read_text(encoding="utf-8")
    guard_start = migration.index("-- A terminal checkout is immutable:")
    event_handler = migration.index(
        "if normalized_status in ('succeeded','confirmed') then", guard_start
    )
    guard = migration[guard_start:event_handler]
    terminal_states = (
        "refunded",
        "reversed",
        "canceled",
        "cancelled",
        "rejected",
        "deadline_expired",
    )
    for state in terminal_states:
        assert f"'{state}'" in guard
    assert "return jsonb_build_object('ignored', true, 'reason', 'checkout_terminal')" in guard
