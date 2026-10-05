import unittest
from unittest.mock import patch
from types import SimpleNamespace

import streamlit as st

import crm_core
import free_automation
import saas_core
from inventory_core import stock_info
from max_operator import can_execute, plan_action


class CoreRegressionTests(unittest.TestCase):
    def setUp(self):
        for key in list(st.session_state):
            if key.startswith("_test_") or key in {
                "_app_leads_cache", "_app_orders_cache", "_app_products_cache",
                "_app_data_revision", "max_data_snapshot",
                "_saas_data_records_leads", "_saas_data_records_orders",
            }:
                st.session_state.pop(key, None)

    def test_inventory_prefers_size_breakdown(self):
        total, by_size, known = stock_info({
            "stock": 99,
            "stock_by_size": {"S": 2, "M": 3, "L": -4},
        })
        self.assertTrue(known)
        self.assertEqual(total, 5)
        self.assertEqual(by_size["L"], 0)

    def test_crm_rejects_immutable_id_and_invalid_status(self):
        with patch.object(crm_core, "data_load", return_value=[]), patch.object(crm_core, "data_save"):
            lead = crm_core.create_lead(name="Test")
            with self.assertRaises(ValueError):
                crm_core.update_lead(lead["id"], id="changed")
            with self.assertRaises(ValueError):
                crm_core.update_lead(lead["id"], status="INVALID")

    def test_order_rejects_immutable_id_and_invalid_status(self):
        with patch.object(free_automation, "data_load", return_value=[]), patch.object(free_automation, "data_save"):
            order = free_automation.create_order(customer="Test")
            with self.assertRaises(ValueError):
                free_automation.update_order(order["id"], id="changed")
            with self.assertRaises(ValueError):
                free_automation.update_order(order["id"], status="INVALID")

    def test_max_write_requires_confirmation(self):
        plan = plan_action("создай контент-план на 7 дней")
        self.assertTrue(plan.requires_confirmation)
        self.assertFalse(can_execute(plan, False))
        self.assertTrue(can_execute(plan, True))

    def test_max_unknown_command_is_not_executable(self):
        plan = plan_action("сделай что-нибудь неизвестное")
        self.assertEqual(plan.action, "unknown")
        self.assertFalse(can_execute(plan, True))

    def test_data_save_conflict_does_not_overwrite_and_invalidates_cache(self):
        st.session_state["_saas_data_records_products"] = {
            "p1": {"payload": {"name": "old"}, "updated_at": "2026-10-05T10:00:00+00:00"}
        }
        with patch.object(saas_core, "saas_enabled", return_value=True), \
             patch.object(saas_core, "can", return_value=True), \
             patch.object(saas_core, "tenant_id", return_value="tenant-1"), \
             patch.object(saas_core, "_rest_post", side_effect=saas_core.SupabaseRequestError("DATA_CONFLICT", 409)):
            with self.assertRaises(saas_core.DataConflictError):
                saas_core.data_save("products", [
                    {"_saas_record_id": "p1", "name": "new"}
                ])
        self.assertNotIn("_saas_data_records_products", st.session_state)

    def test_data_save_denies_write_for_read_only_role(self):
        with patch.object(saas_core, "saas_enabled", return_value=True), \
             patch.object(saas_core, "can", return_value=False):
            with self.assertRaises(PermissionError):
                saas_core.data_save("products", [{"name": "blocked"}])


if __name__ == "__main__":
    unittest.main()
