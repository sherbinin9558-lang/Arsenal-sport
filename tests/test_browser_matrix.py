import unittest

from scripts.browser_matrix import VIEWPORTS


class BrowserMatrixTests(unittest.TestCase):
    def test_required_responsive_viewports_are_defined(self):
        self.assertEqual(VIEWPORTS["desktop"], {"width": 1440, "height": 1000})
        self.assertEqual(VIEWPORTS["tablet"], {"width": 1024, "height": 900})
        self.assertEqual(VIEWPORTS["mobile"], {"width": 390, "height": 844})

    def test_viewport_names_are_stable(self):
        self.assertEqual(list(VIEWPORTS), ["desktop", "tablet", "mobile"])


if __name__ == "__main__":
    unittest.main()
