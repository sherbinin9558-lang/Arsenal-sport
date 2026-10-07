from max_operator import can_execute, plan_action

def test_prepare_today_requires_confirmation():
    plan = plan_action("подготовь контент на сегодня")
    assert plan.action == "prepare_today"
    assert plan.mode == "write"
    assert plan.requires_confirmation
    assert not can_execute(plan, approved=False)
    assert can_execute(plan, approved=True)
