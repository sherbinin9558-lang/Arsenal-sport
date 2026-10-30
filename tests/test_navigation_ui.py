"""Contract tests for the live workspace navigation presentation."""
import unittest

from ui.navigation import WORKSPACE_NAV_CSS


class WorkspaceNavigationTests(unittest.TestCase):
    def test_styles_are_scoped_to_main_workspace_tabs(self):
        self.assertIn(".st-key-main_workspace_tabs", WORKSPACE_NAV_CSS)
        self.assertIn("aria-selected=\"true\"", WORKSPACE_NAV_CSS)

    def test_mobile_navigation_remains_horizontally_scrollable(self):
        self.assertIn("overflow-x: auto", WORKSPACE_NAV_CSS)
        self.assertIn("@media (max-width: 768px)", WORKSPACE_NAV_CSS)
        self.assertIn("scroll-snap-type: x proximity", WORKSPACE_NAV_CSS)

    def test_keyboard_focus_and_reduced_motion_are_supported(self):
        self.assertIn(":focus-visible", WORKSPACE_NAV_CSS)
        self.assertIn("prefers-reduced-motion: reduce", WORKSPACE_NAV_CSS)


if __name__ == "__main__":
    unittest.main()
