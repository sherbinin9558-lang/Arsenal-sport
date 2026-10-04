import unittest

try:
    import ui.max as max_ui
    HAS_DEPS = True
except Exception:  # CI without streamlit/Pillow
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "streamlit and Pillow are required")
class MaxModuleNamesTests(unittest.TestCase):
    """Names that render_max() uses must exist at module level (they were once undefined)."""

    def test_names_used_by_render_max_are_defined(self):
        for name in ("CRM_STATUSES", "content_bundle", "max_product_title", "get_logo"):
            self.assertTrue(hasattr(max_ui, name), name)
        self.assertIn("Новый", max_ui.CRM_STATUSES)


if __name__ == "__main__":
    unittest.main()
