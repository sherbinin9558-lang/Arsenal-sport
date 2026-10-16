"""Performance contracts for growth analytics caching."""
import app_data


def test_cached_growth_recommendations_uses_correct_argument_order_and_reuses_cache(monkeypatch):
    app_data.st.session_state.clear()
    calls = []

    def fake_ai_summary(products, leads, orders, plan):
        calls.append((products, leads, orders, plan))
        return {"recommendations": ["cached recommendation"]}

    monkeypatch.setattr(app_data, "ai_summary", fake_ai_summary)
    products = [{"name": "Ball"}]
    leads = [{"product": "Ball"}]
    orders = [{"product": "Ball"}]
    plan = [{"product": "Ball"}]

    assert app_data._cached_growth_recommendations(products, leads, orders, plan) == [
        "cached recommendation"
    ]
    # New list objects are created by data loaders on Streamlit reruns. The
    # tenant/revision/length cache should avoid recomputing the same analysis.
    assert app_data._cached_growth_recommendations(
        list(products), list(leads), list(orders), list(plan)
    ) == ["cached recommendation"]

    assert len(calls) == 1
    _, actual_leads, actual_orders, actual_plan = calls[0]
    assert actual_leads is leads
    assert actual_orders is orders
    assert actual_plan is plan
