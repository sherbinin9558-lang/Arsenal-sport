"""Regression contracts for the ShopPilot live product shell."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShopPilotBrandingTests(unittest.TestCase):
    def test_live_app_uses_shop_pilot_product_brand(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('page_title="ShopPilot AI"', source)
        self.assertIn("SHOPPILOT AI", source)
        self.assertIn("Контент-студия", source)
        self.assertNotIn("AI Agent Content Manager", source)
        self.assertNotIn("AI AGENT CONTENT MANAGER", source)

    def test_live_dashboard_uses_approved_tagline_and_robot_asset(self):
        source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("Робот трудится", source)
        self.assertIn("assets/shoppilot_robot.jpg", source)
        self.assertIn("assets/shoppilot_logo.png", (ROOT / "app.py").read_text(encoding="utf-8"))

    def test_tenant_name_remains_dynamic(self):
        source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('st.session_state.get("saas_tenant_name"', source)
        self.assertIn("_safe_tenant_label(store_name)", source)


if __name__ == "__main__":
    unittest.main()
