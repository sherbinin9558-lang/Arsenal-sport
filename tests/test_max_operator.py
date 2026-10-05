import datetime as dt

from max_operator import (
    ActionPlan,
    build_business_snapshot,
    can_execute,
    plan_action,
    resolve_action,
)


def test_read_command_is_safe_without_confirmation():
    plan = plan_action("покажи продажи и конверсию")
    assert plan.action == "sales_summary"
    assert plan.mode == "read"
    assert plan.requires_confirmation is False
    assert can_execute(plan, approved=False)


def test_write_command_requires_explicit_confirmation():
    plan = plan_action("создай контент-план на 7 дней")
    assert plan.action == "create_7_day_plan"
    assert plan.mode == "write"
    assert plan.requires_confirmation is True
    assert not can_execute(plan, approved=False)
    assert can_execute(plan, approved=True)


def test_unknown_command_never_executes():
    plan = plan_action("сделай что-нибудь")
    assert plan.action == "unknown"
    assert not can_execute(plan, approved=True)


def test_snapshot_is_deterministic_in_shape():
    snapshot = build_business_snapshot(
        [{"name": "A"}],
        [{"id": "lead"}],
        [{"amount": "1200", "status": "Новая"}, {"total": 800, "status": "Завершён"}],
        [{"date": "2026-10-05"}],
    )
    assert snapshot["products"] == 1
    assert snapshot["leads"] == 1
    assert snapshot["orders"] == 2
    assert snapshot["active_orders"] == 1
    assert snapshot["content_items"] == 1
    assert snapshot["revenue"] == 2000.0
    dt.datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))


def test_supported_intents_have_registry():
    for command in (
        "проверь остатки",
        "контент на сегодня",
        "анализ магазина",
        "создай план контента на неделю",
    ):
        plan = plan_action(command)
        assert plan.action != "unknown"
