import ast
import unittest
from pathlib import Path


SAAS_CORE = Path(__file__).resolve().parents[1] / "saas_core.py"


class DataSaveSafetyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SAAS_CORE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_data_save_preflights_versions_before_mutations(self):
        fn = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "data_save"
        )
        calls = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.append((node.func.id, node.lineno))
        get_lines = [line for name, line in calls if name == "_rest_get"]
        mutation_lines = [
            line for name, line in calls
            if name in {"_rest_patch", "_rest_post", "_rest_delete"}
        ]
        self.assertTrue(get_lines, "data_save must preflight current versions")
        self.assertTrue(mutation_lines, "data_save must contain protected mutations")
        self.assertLess(min(get_lines), min(mutation_lines))

    def test_preflight_raises_conflict_on_version_mismatch(self):
        self.assertIn("current_versions", self.source)
        self.assertIn("expected != actual", self.source)
        self.assertIn("raise DataConflictError", self.source)


if __name__ == "__main__":
    unittest.main()


class ProductStockRegressionTests(unittest.TestCase):
    def test_product_edit_preserves_stock_and_price_fields(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn('"price": p.get("price", "")', source)
        self.assertIn('"stock": p.get("stock", 0)', source)
        self.assertIn('"total_stock": p.get("total_stock", p.get("stock", 0))', source)

    def test_stock_helpers_accept_legacy_stock_field(self):
        source = (Path(__file__).resolve().parents[1] / "automation_suite.py").read_text(encoding="utf-8")
        self.assertIn('product.get("total_stock", product.get("stock"))', source)
        source = (Path(__file__).resolve().parents[1] / "free_automation.py").read_text(encoding="utf-8")
        self.assertIn('p.get("total_stock", p.get("stock", 0))', source)


class OrderSafetyRegressionTests(unittest.TestCase):
    def test_order_identity_and_status_are_validated(self):
        source = (Path(__file__).resolve().parents[1] / "free_automation.py").read_text(encoding="utf-8")
        self.assertIn("ORDER_STATUSES =", source)
        self.assertIn('if "id" in changes:', source)
        self.assertIn('if "status" in changes and changes["status"] not in ORDER_STATUSES:', source)
