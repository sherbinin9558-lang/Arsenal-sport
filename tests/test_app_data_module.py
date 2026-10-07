"""Regression contract for the first app.py decomposition slice."""

from app_data import (
    _find_record_index,
    attribution_metrics,
    max_product_title,
)


def test_app_data_exposes_moved_data_helpers():
    rows = [{"_saas_record_id": "r1", "name": "Ball"}]
    assert max_product_title(rows[0]) == "Ball"
    assert _find_record_index(rows, "r1") == 0
    assert attribution_metrics(
        [{"product_id": "r1", "leads": 2, "orders": 1}], [], []
    )["r1"] == {"content": 1, "leads": 2, "orders": 1}
