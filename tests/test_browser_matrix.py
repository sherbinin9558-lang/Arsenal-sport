import unittest

from scripts.browser_matrix import VIEWPORTS


class BrowserMatrixTests(unittest.TestCase):
    def test_required_responsive_viewports_are_defined(self):
        self.assertEqual(VIEWPORTS["desktop"], {"width": 1440, "height": 1000})
        self.assertEqual(VIEWPORTS["tablet"], {"width": 1024, "height": 900})
        self.assertEqual(VIEWPORTS["mobile"], {"width": 390, "height": 844})

    def test_viewport_names_are_stable(self):
        self.assertEqual(list(VIEWPORTS), ["desktop", "tablet", "mobile"])

    def test_production_smoke_rejects_streamlit_status_embed_without_app_marker(self):
        from scripts.playwright_production_smoke import validate_application_content

        status_only = (
            "Status embed installed. This will be shown if an incident or maintenance "
            "is posted on your status page. View latest updates"
        )
        with self.assertRaisesRegex(RuntimeError, "status/maintenance"):
            validate_application_content(status_only)

    def test_production_smoke_requires_actual_app_marker(self):
        from scripts.playwright_production_smoke import validate_application_content

        with self.assertRaisesRegex(RuntimeError, "Expected application marker"):
            validate_application_content("Streamlit is starting…")

    def test_production_smoke_accepts_expected_login_page_marker(self):
        from scripts.playwright_production_smoke import validate_application_content

        validate_application_content("Please sign in. Ваш магазин. Один рабочий центр. Email Пароль")


if __name__ == "__main__":
    unittest.main()
