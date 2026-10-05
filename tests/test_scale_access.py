import unittest
from unittest.mock import patch

import streamlit as st

import saas_core


class ScaleAccessTests(unittest.TestCase):
    def setUp(self):
        for key in ("saas_access_token", "saas_tenant_id", "_saas_data_page_cache"):
            st.session_state.pop(key, None)
        st.session_state["saas_access_token"] = "test-token"
        st.session_state["saas_tenant_id"] = "tenant-1"

    def test_data_count_uses_count_header_without_loading_rows(self):
        with patch.object(saas_core, "saas_enabled", return_value=True),              patch.object(saas_core, "_rest_get_paged", return_value=([], 123)) as paged:
            self.assertEqual(saas_core.data_count("products"), 123)
        params = paged.call_args.kwargs["params"]
        self.assertEqual(params["entity"], "eq.products")
        self.assertEqual(params["tenant_id"], "eq.tenant-1")

    def test_keyset_cursor_builds_stable_descending_boundary(self):
        rows = [
            {"record_id": f"r{i}", "payload": {"name": str(i)}, "created_at": f"2026-10-05T{10-i:02d}:00:00Z", "updated_at": None}
            for i in range(10, 0, -1)
        ]
        with patch.object(saas_core, "saas_enabled", return_value=True),              patch.object(saas_core, "_rest_get", return_value=rows) as get:
            result = saas_core.data_load_keyset(
                "products",
                page_size=10,
                cursor={"created_at": "2026-10-05T11:00:00Z", "record_id": "r9"},
            )
        params = get.call_args.kwargs["params"]
        self.assertEqual(
            params["or"],
            "or(created_at.lt.2026-10-05T11:00:00Z,and(created_at.eq.2026-10-05T11:00:00Z,record_id.lt.r9))",
        )
        self.assertEqual(result["next_cursor"]["record_id"], "r1")

    def test_keyset_search_is_preserved_with_cursor(self):
        rows = [{"record_id": "r1", "payload": {"name": "Nike"}, "created_at": "2026-10-05T10:00:00Z", "updated_at": None}]
        with patch.object(saas_core, "saas_enabled", return_value=True), \
             patch.object(saas_core, "_rest_get", return_value=rows) as get:
            saas_core.data_load_keyset(
                "products",
                page_size=10,
                search="Nike",
                cursor={"created_at": "2026-10-05T11:00:00Z", "record_id": "r9"},
            )
        params = get.call_args.kwargs["params"]
        self.assertIn("and", params)
        self.assertIn("payload->>name.ilike.*Nike*", params["and"])
        self.assertIn("created_at.lt.2026-10-05T11:00:00Z", params["and"])

    def test_data_group_count_uses_rpc_in_saas_mode(self):
        with patch.object(saas_core, "saas_enabled", return_value=True), \
             patch.object(saas_core, "_request", return_value=[{"value": "Футболка", "count": 12}]) as request:
            self.assertEqual(saas_core.data_group_count("products", "category")[0]["count"], 12)
        self.assertEqual(request.call_args.args[:2], ("POST", "/rest/v1/rpc/app_data_group_count"))
        self.assertEqual(request.call_args.kwargs["json"], {"p_entity": "products", "p_field": "category"})

    def test_usage_snapshot_uses_database_counts_in_saas_mode(self):
        with patch.object(saas_core, "saas_enabled", return_value=True),              patch.object(saas_core, "data_count", side_effect=[7, 3, 5, 9]):
            self.assertEqual(
                saas_core.usage_snapshot(),
                {"products": 7, "leads": 3, "orders": 5, "content": 9},
            )



    def test_dashboard_snapshot_uses_rpc_in_saas_mode(self):
        import saas_core
        from unittest.mock import patch
        with patch.object(saas_core, "saas_enabled", return_value=True),              patch.object(saas_core.st.session_state, "get", side_effect=lambda key, default=None: "access-token" if key == "saas_access_token" else default),              patch.object(saas_core, "_request", return_value={
                 "products": {"total": 12000, "low_stock": 8},
                 "leads": {"total": 400},
                 "orders": {"total": 90, "active": 20, "completed": 60, "cancelled": 10, "amount": 123456},
                 "content": {"total": 800, "review": 4, "overdue": 3, "due_today": 2},
                 "low_stock_products": [],
             }) as request:
            snapshot = saas_core.dashboard_snapshot()
        self.assertEqual(snapshot["products"]["total"], 12000)
        self.assertEqual(snapshot["orders"]["amount"], 123456)
        request.assert_called_once()
        self.assertIn("app_data_dashboard_summary", request.call_args.args[1])

if __name__ == "__main__":
    unittest.main()
