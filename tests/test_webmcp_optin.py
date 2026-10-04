import unittest
from unittest.mock import MagicMock, patch

import webmcp_tools


class WebMCPOptInTests(unittest.TestCase):
    def test_disabled_by_default_and_never_mounts_the_component(self):
        component = MagicMock()
        with patch.object(webmcp_tools, "_cfg", lambda name, default="": default), \
             patch.object(webmcp_tools, "_WEBMCP_COMPONENT", component):
            self.assertFalse(webmcp_tools.webmcp_enabled())
            webmcp_tools.mount_webmcp_tools()
        component.assert_not_called()

    def test_enabled_by_flag_mounts_with_store_data(self):
        component = MagicMock()
        with patch.object(webmcp_tools, "_cfg", lambda name, default="": "true" if name == "ENABLE_WEBMCP" else default), \
             patch.object(webmcp_tools, "_WEBMCP_COMPONENT", component), \
             patch.object(webmcp_tools, "_webmcp_data", return_value={"products": []}):
            self.assertTrue(webmcp_tools.webmcp_enabled())
            webmcp_tools.mount_webmcp_tools()
        component.assert_called_once()

    def test_only_explicit_truthy_values_enable_it(self):
        for value, expected in (("1", True), ("yes", True), ("false", False), ("", False), ("no", False)):
            with patch.object(webmcp_tools, "_cfg", lambda name, default="", v=value: v):
                self.assertEqual(webmcp_tools.webmcp_enabled(), expected, value)


if __name__ == "__main__":
    unittest.main()
