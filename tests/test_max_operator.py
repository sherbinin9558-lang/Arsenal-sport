import datetime as dt
from max_operator import build_business_snapshot, can_execute, plan_action, resolve_action

def test_read_command_is_safe_without_confirmation():
    plan=plan_action("покажи продажи и конверсию")
    assert plan.action=="sales_summary" and plan.mode=="read" and not plan.requires_confirmation
    assert can_execute(plan,approved=False)

def test_write_command_requires_explicit_confirmation():
    plan=plan_action("создай контент-план на 7 дней")
    assert plan.action=="create_7_day_plan" and plan.mode=="write" and plan.requires_confirmation
    assert not can_execute(plan,approved=False)
    assert can_execute(plan,approved=True)

def test_unknown_command_never_executes():
    plan=plan_action("сделай что-нибудь")
    assert plan.action=="unknown"
    assert not can_execute(plan,approved=True)

def test_snapshot_shape_and_revenue():
    snapshot=build_business_snapshot([{"name":"A"}],[{"id":"lead"}],[{"amount":"1200","status":"Новая"},{"total":800,"status":"Завершён"}],[{"date":"2026-10-05"}])
    assert snapshot["products"]==1
    assert snapshot["leads"]==1
    assert snapshot["orders"]==2
    assert snapshot["active_orders"]==1
    assert snapshot["content_items"]==1
    assert snapshot["revenue"]==2000.0
    dt.datetime.fromisoformat(snapshot["generated_at"])

def test_supported_intents():
    for command in ("проверь остатки","контент на сегодня","анализ магазина","создай план контента на неделю"):
        assert resolve_action(command) is not None
