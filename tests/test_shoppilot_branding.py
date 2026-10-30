"""Regression contracts for the ShopPilot live product shell."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShopPilotBrandingTests(unittest.TestCase):
    def test_live_app_uses_shop_pilot_product_brand(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('page_title="ShopPilot AI"', source)
        self.assertIn("ShopPilot AI", source)
        self.assertIn("Контент-студия", source)
        self.assertNotIn("AI Agent Content Manager", source)
        self.assertNotIn("AI AGENT CONTENT MANAGER", source)
        self.assertNotIn("ai_agent_content_manager", source.casefold())
        self.assertIn("#ShopPilotAI", source)
        self.assertIn("shoppilot_reel.mp4", source)
        self.assertIn("Контент-студия", source)
        self.assertIn("План публикаций", source)
        self.assertIn('brand_title_color = "#f4f6ff" if dark_mode else "#171a21"', source)

    def test_settings_and_max_use_current_product_brand(self):
        settings = (ROOT / "ui" / "settings.py").read_text(encoding="utf-8")
        max_ui = (ROOT / "ui" / "max.py").read_text(encoding="utf-8")
        self.assertIn("ShopPilot AI", settings)
        self.assertIn("ShopPilot AI", max_ui)
        self.assertNotIn("AI Agent Content Manager", settings)
        self.assertNotIn("AI Agent Content Manager", max_ui)

    def test_live_dashboard_uses_approved_tagline_and_robot_asset(self):
        source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("Робот трудится", source)
        self.assertIn("assets/shoppilot_robot.jpg", source)
        self.assertIn("assets/shoppilot_logo.png", (ROOT / "app.py").read_text(encoding="utf-8"))

    def test_tenant_name_remains_dynamic(self):
        source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('st.session_state.get("saas_tenant_name"', source)
        self.assertIn("_safe_tenant_label(store_name)", source)

    def test_public_login_uses_shop_pilot_brand(self):
        source = (ROOT / "saas_core.py").read_text(encoding="utf-8")
        self.assertIn('public-brand-name">ShopPilot AI</div>', source)
        self.assertNotIn("public-brand-name">AI Agent Content Manager", source)

    def test_generated_cards_use_shop_pilot_platform_watermark(self):
        source = (ROOT / "card_generator.py").read_text(encoding="utf-8")
        self.assertIn('"SHOPPILOT AI"', source)
        self.assertIn('brand or "ShopPilot AI"', source)
        self.assertNotIn("AI AGENT CONTENT MANAGER", source)
        self.assertNotIn("AI Agent Content Manager", source)


if __name__ == "__main__":
    unittest.main()
