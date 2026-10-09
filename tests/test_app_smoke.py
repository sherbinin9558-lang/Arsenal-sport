"""Open the app and every MAX section in demo mode; none of them may raise.

Skipped automatically when streamlit is not installed (for example in the minimal CI).
"""
import os
import sys
import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
    HAS_STREAMLIT = True
except Exception:
    HAS_STREAMLIT = False

ROOT = Path(__file__).resolve().parents[1]
MAX_SECTIONS = ["Обзор", "Аккаунт", "Настройки", "AI-продавец", "CRM",
                "Заказы", "Склад", "Контент", "Автоматизация", "Аналитика"]


def _max_script():
    import streamlit as st
    from saas_core import _set_identity
    if "saas_demo" not in st.session_state:
        st.session_state["saas_demo"] = True
        _set_identity({"id": "demo-user", "email": "demo@example.com"},
                      {"id": "demo-tenant", "name": "Demo", "plan": "pro", "status": "active"})
    from ui.max import render_max
    render_max()


@unittest.skipUnless(HAS_STREAMLIT, "streamlit is required")
class AppSmokeTests(unittest.TestCase):
    def setUp(self):
        self._old = {k: os.environ.get(k) for k in ("DEMO_MODE", "SUPABASE_URL", "SUPABASE_ANON_KEY")}
        os.environ["DEMO_MODE"] = "true"
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_ANON_KEY", None)
        self._cwd = os.getcwd()
        os.chdir(ROOT)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        sys.modules.pop("webmcp_tools", None)  # the test runner starts a fresh component registry

    def tearDown(self):
        os.chdir(self._cwd)
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_main_page_renders(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
        self.assertEqual([e.value for e in at.exception], [])


    def test_mobile_and_light_theme_css_keeps_controls_readable(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('[data-baseweb="select"] > div {background:#ffffff!important;color:#17151c!important;', source)
        self.assertIn('[data-baseweb="select"] svg {fill:#4b5565!important;color:#4b5565!important;', source)
        self.assertIn('header[data-testid="stHeader"],[data-testid="stToolbar"]{background:var(--chrome-bg,#f6f7fb)!important;', source)

    def test_max_dialog_css_is_mobile_bounded(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("max-height:calc(100dvh - 24px", source)
        self.assertIn("width:calc(100vw - 24px)", source)
        self.assertNotIn("position:fixed!important;inset:0!important;z-index:2147483647", source)
        self.assertIn('header[data-testid="stHeader"],[data-testid="stToolbar"]{background:var(--chrome-bg,#f6f7fb)!important;', source)


    def test_dark_theme_is_not_overridden_by_global_light_background(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--app-bg:#0b0e13;--sidebar-bg:#10131a;--chrome-bg:#0b0e13;", source)
        self.assertIn("background:var(--app-bg)!important", source)
        self.assertIn("background:var(--sidebar-bg,#ffffff)!important", source)

    def test_tbank_return_does_not_activate_on_authorized_status(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('if status == "CONFIRMED" and plan in ("starter","pro","business") and pid:', source)
        self.assertNotIn('if status in ("CONFIRMED","AUTHORIZED")', source)

    def test_mobile_tables_stay_within_viewport_and_can_scroll(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('[data-testid="stDataFrame"],[data-testid="stTable"]{box-sizing:border-box!important;width:100%!important;max-width:100%!important;min-width:0!important;overflow-x:auto!important;', source)
        self.assertIn("-webkit-overflow-scrolling:touch!important", source)
        self.assertIn('[data-testid="stTable"] table{min-width:560px!important;}', source)

    def test_every_max_section_renders(self):
        at = AppTest.from_function(_max_script, default_timeout=120).run()
        self.assertEqual([e.value for e in at.exception], [])
        for section in MAX_SECTIONS:
            with self.subTest(section=section):
                at.radio(key="max_section").set_value(section).run()
                self.assertEqual([e.value for e in at.exception], [], section)


if __name__ == "__main__":
    unittest.main()
