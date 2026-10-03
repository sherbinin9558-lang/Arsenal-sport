import ast
import unittest
from pathlib import Path


SAAS_CORE = Path(__file__).resolve().parents[1] / "saas_core.py"


class DataSaveSafetyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SAAS_CORE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_data_save_uses_atomic_batch_rpc(self):
        fn = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "data_save"
        )
        rpc_calls = []
        direct_mutations = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "_rest_post":
                    rpc_calls.append(node)
                if node.func.id in {"_rest_patch", "_rest_delete"}:
                    direct_mutations.append(node)
        self.assertTrue(rpc_calls, "data_save must persist SaaS changes through the atomic RPC")
        self.assertFalse(direct_mutations, "data_save must not perform partial direct mutations")
        self.assertIn("save_app_data_batch", self.source)

    def test_data_save_builds_new_update_and_delete_items(self):
        self.assertIn('"is_new":True', self.source)
        self.assertIn('"is_deleted":True', self.source)
        self.assertIn('"expected_updated_at":baseline[record_id].get("updated_at")', self.source)
        self.assertIn('data_load(entity,[])', self.source)

    def test_preflight_raises_conflict_on_version_mismatch(self):
        self.assertIn("current_versions", self.source)
        self.assertIn("expected != actual", self.source)
        self.assertIn("raise DataConflictError", self.source)


class ProductStockRegressionTests(unittest.TestCase):
    def test_product_edit_preserves_stock_and_price_fields(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn('"price": p.get("price", "")', source)
        self.assertIn('"stock": p.get("stock", 0)', source)
        self.assertIn('"total_stock": p.get("total_stock", p.get("stock", 0))', source)

    def test_stock_helpers_accept_legacy_stock_field(self):
        source = (Path(__file__).resolve().parents[1] / "inventory_core.py").read_text(encoding="utf-8")
        self.assertIn('product.get("total_stock", product.get("stock"))', source)
        automation = (Path(__file__).resolve().parents[1] / "automation_suite.py").read_text(encoding="utf-8")
        self.assertIn("from inventory_core import stock_info as _stock_info", automation)
        free = (Path(__file__).resolve().parents[1] / "free_automation.py").read_text(encoding="utf-8")
        self.assertIn("from inventory_core import stock_info", free)


class OrderSafetyRegressionTests(unittest.TestCase):
    def test_order_identity_and_status_are_validated(self):
        source = (Path(__file__).resolve().parents[1] / "free_automation.py").read_text(encoding="utf-8")
        self.assertIn("ORDER_STATUSES =", source)
        self.assertIn("ORDER_IMMUTABLE_FIELDS =", source)
        self.assertIn("created_at", source)
        self.assertIn('if "status" in changes and changes["status"] not in ORDER_STATUSES:', source)

    def test_order_immutable_fields_are_rejected(self):
        from free_automation import ORDER_IMMUTABLE_FIELDS
        self.assertEqual(ORDER_IMMUTABLE_FIELDS, frozenset({"id", "created_at"}))


class CrmSafetyRegressionTests(unittest.TestCase):
    def test_lead_identity_and_status_are_validated(self):
        source = (Path(__file__).resolve().parents[1] / "crm_core.py").read_text(encoding="utf-8")
        self.assertIn('if "id" in changes:', source)
        self.assertIn('if "status" in changes and changes["status"] not in STATUSES:', source)


class RlsRoleSafetyRegressionTests(unittest.TestCase):
    def test_owner_role_cannot_be_changed_by_member_role_rpc(self):
        source = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")
        self.assertIn("CANNOT_CHANGE_OWNER_ROLE", source)
        self.assertIn("if target_current_role = 'owner' then", source)
        self.assertIn("for update;", source)


class UploadSafetyRegressionTests(unittest.TestCase):
    def test_product_image_extensions_are_whitelisted(self):
        source = (Path(__file__).resolve().parents[1] / "automation_suite.py").read_text(encoding="utf-8")
        self.assertIn('if ext not in {".jpg", ".jpeg", ".png", ".webp"}:', source)
        self.assertIn("Поддерживаются только JPG, JPEG, PNG и WEBP.", source)


class InventoryRegressionTests(unittest.TestCase):
    def test_stock_source_prefers_size_breakdown_then_total_stock(self):
        from inventory_core import stock_info
        self.assertEqual(stock_info({"stock_by_size": {"42": 2, "43": 3}, "total_stock": 99})[0], 5)
        self.assertEqual(stock_info({"total_stock": 7, "stock": 99})[0], 7)
        self.assertEqual(stock_info({"stock": 4})[0], 4)


class ContentIdentityRegressionTests(unittest.TestCase):
    def test_saas_record_id_is_used_for_stable_content_identity(self):
        source = (Path(__file__).resolve().parents[1] / "content_manager.py").read_text(encoding="utf-8")
        self.assertIn('item.get("_saas_record_id")', source)
        self.assertIn('item.get("content_id")', source)

    def test_existing_content_id_is_preserved(self):
        from content_manager import content_identity
        item = {"content_id": "cnt-existing", "date": "2026-10-01", "idea": "old"}
        self.assertEqual(content_identity(item), "cnt-existing")


class DemoModeRecordRegressionTests(unittest.TestCase):
    def test_record_index_helper_supports_local_mode_indices(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("if isinstance(record_id, int):", source)
        self.assertIn('p.get("_saas_record_id") or real_i', source)
        self.assertIn('item.get("_saas_record_id") or ri', source)
        self.assertIn('reel_product.get("_saas_record_id") or st.session_state.get("r_sel", 0)', source)


if __name__ == "__main__":
    unittest.main()
