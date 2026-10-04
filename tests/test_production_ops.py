import unittest
from unittest.mock import patch

import production_ops


class TestProductionOps(unittest.TestCase):
    def test_provider_health_skips_without_credentials(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "VK_TOKEN": ""}, clear=False):
            result = production_ops.provider_health()
        self.assertEqual(result["telegram"]["status"], "skipped")
        self.assertEqual(result["vk"]["status"], "skipped")

    def test_provider_health_never_returns_token(self):
        with patch("production_ops._http_json", return_value=(True, 200, 0.01, {"ok": True, "result": {"id": 1, "is_bot": True, "username": "bot"}})):
            result = production_ops.telegram_health("123456789:SECRET")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("SECRET", str(result))

    def test_agent_allowlist_and_limits(self):
        clean = production_ops.validate_agent_payload("create_task", {"title": "Task"})
        self.assertEqual(clean["title"], "Task")
        with self.assertRaises(ValueError):
            production_ops.validate_agent_payload("create_task", {"title": "x", "shell": "rm"})
        with self.assertRaises(ValueError):
            production_ops.validate_agent_payload("queue_instagram_draft", {"caption": "x" * 2201})

    def test_expired_agent_is_detected(self):
        self.assertTrue(production_ops.agent_is_expired("2000-01-01T00:00:00Z"))
        self.assertFalse(production_ops.agent_is_expired("2099-01-01T00:00:00Z"))


    @patch("production_ops.data_load", return_value=[])
    @patch("production_ops.data_save")
    @patch("production_ops.can", return_value=True)
    def test_audit_redacts_sensitive_fields(self, can_mock, save_mock, load_mock):
        row = production_ops.audit_event("provider_check", details={"token": "hidden-value", "note": "ok"})
        self.assertEqual(row["details"]["token"], "[REDACTED]")
        self.assertEqual(row["details"]["note"], "ok")

    @patch("production_ops.data_load", return_value=[])
    def test_operations_health_is_read_only_without_credentials(self, load_mock):
        result = production_ops.operations_health()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["providers"]["telegram"]["status"], "skipped")
        self.assertEqual(result["providers"]["vk"]["status"], "skipped")

    def test_future_agent_timestamp_is_invalid(self):
        self.assertTrue(production_ops.agent_is_expired("2099-01-01T00:00:00Z"))

if __name__ == "__main__":
    unittest.main()
