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
        self.assertIn("st-key-sidebar_identity", source)
        self.assertIn("st-key-sidebar_max_card", source)
        self.assertIn("st-key-sidebar_preferences", source)
        self.assertIn("st-key-sidebar_store_context", source)
        self.assertIn("st-key-sidebar_account", source)
        self.assertIn("sidebar-quick-overview", source)
        self.assertIn("render_sidebar_overview()", source)
        self.assertIn("render_account_bar()", source)

    def test_full_visual_system_is_applied_without_replacing_navigation(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        visual = (ROOT / "ui" / "visual_system.py").read_text(encoding="utf-8")
        self.assertIn("apply_shoppilot_visual_system(st, dark_mode=dark_mode)", source)
        self.assertIn("main_workspace_tabs", source)
        self.assertIn("sidebar_identity", source)
        self.assertIn("dashboard-hero", visual)
        self.assertIn("stMetric", visual)
        self.assertIn("prefers-reduced-motion", visual)


    def test_dashboard_places_four_reference_kpis_before_secondary_guidance(self):
        dashboard = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('d1, d2, d3, d4 = st.columns(4)', dashboard)
        self.assertIn('d1.metric("Товары", products_total', dashboard)
        self.assertIn('d2.metric("Контент", wm.get("total", 0)', dashboard)
        self.assertIn('d3.metric("Заявки", crm.get("total", 0)', dashboard)
        self.assertIn('d4.metric("Заказы", om.get("total", 0)', dashboard)
        self.assertLess(dashboard.index('d1.metric("Товары"'), dashboard.index('st.markdown("---")'))
        self.assertNotIn('st.caption(f"Рабочее пространство:', dashboard)
        self.assertIn('sales_kpi.metric("Сумма заказов"', dashboard)
        self.assertIn('conversion_kpi.metric("Конверсия"', dashboard)

    def test_dashboard_matches_dark_blue_reference_without_changing_brand_assets(self):
        visual = (ROOT / "ui" / "visual_system.py").read_text(encoding="utf-8")
        dashboard = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("st-key-dashboard_hero_shell", visual)
        self.assertIn("linear-gradient(112deg,#10427c", visual)
        self.assertIn("background:linear-gradient(145deg,#123765", visual)
        self.assertNotIn("--sp-canvas:#f2f5fb", visual)
        self.assertIn('with st.container(key="dashboard_hero_shell")', dashboard)
        self.assertIn('st.image("assets/shoppilot_robot.jpg"', dashboard)
        self.assertIn('st.image("assets/shoppilot_logo.png"', app)

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
        self.assertIn('assets" / "shoppilot_logo.png', source)
        self.assertIn('class="public-logo-image"', source)
        self.assertIn('alt="ShopPilot AI"', source)
        self.assertNotIn('public-logo">AI</div>', source)
        self.assertNotIn('public-brand-name">AI Agent Content Manager', source)

    def test_generated_cards_use_shop_pilot_platform_watermark(self):
        source = (ROOT / "card_generator.py").read_text(encoding="utf-8")
        self.assertIn('"SHOPPILOT AI"', source)
        self.assertIn('brand or "ShopPilot AI"', source)
        self.assertNotIn("AI AGENT CONTENT MANAGER", source)
        self.assertNotIn("AI Agent Content Manager", source)


    def test_visual_system_respects_existing_theme_toggle(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        visual = (ROOT / "ui" / "visual_system.py").read_text(encoding="utf-8")
        self.assertIn('dark_mode = st.toggle("🌙 Тёмная тема", value=True, key="theme_toggle")', app)
        self.assertIn("apply_shoppilot_visual_system(st, dark_mode=dark_mode)", app)
        self.assertIn("if not dark_mode:", visual)
        self.assertIn('aria-selected="true"] *{color:#fff!important', visual)
        # Disabling dark mode must restore a light sidebar after the premium
        # dark sidebar rules are injected earlier in app.py.
        self.assertIn("if not dark_mode:", app)
        self.assertIn("background:linear-gradient(180deg,#fff 0%,#f4f6fb 100%)", app)
        self.assertIn("color:#20283a !important", app)


    def test_dashboard_preserves_legacy_workflows_and_robot_banner(self):
        dashboard = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
        required_existing_workflows = [
            "### Контент и задачи",
            "### Склад",
            "### Продажи",
            'with st.expander("🔗 Контент → продажи"',
            'st.button("➕ Добавить товар"',
            'st.button("📅 Добавить материал в план"',
            'with st.form("dashboard_quick_add_form"',
            'with st.form("dashboard_quick_plan_form"',
            "### Состояние системы",
            "growth_recommendations",
            "attribution_loader",
            'st.image("assets/shoppilot_robot.jpg"',
        ]
        for marker in required_existing_workflows:
            with self.subTest(marker=marker):
                self.assertIn(marker, dashboard)

        # The reference-only chart and completion ring are not backed by
        # existing dashboard data, so do not introduce fabricated metrics.
        self.assertNotIn("78%", dashboard)


    def test_dark_visual_system_overrides_legacy_light_text_colors(self):
        visual = (ROOT / "ui" / "visual_system.py").read_text(encoding="utf-8")
        self.assertIn(".stApp h1,.stApp h2,.stApp h3", visual)
        self.assertIn("[data-testid=\"stMarkdownContainer\"] p", visual)
        self.assertIn("color:var(--sp-text)!important", visual)

    def test_sidebar_help_block_is_valid_python(self):
        import ast
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        ast.parse(source)


if __name__ == "__main__":
    unittest.main()
