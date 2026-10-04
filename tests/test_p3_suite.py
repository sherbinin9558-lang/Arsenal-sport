import unittest
from unittest.mock import patch

import p3_suite

class TestP3Suite(unittest.TestCase):
    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_notification_lifecycle(self, can_mock, save_mock, load_mock):
        row = p3_suite.create_notification("Test", "Body")
        self.assertEqual(row["read"], False)
        load_mock.return_value = [row]
        self.assertTrue(p3_suite.mark_notification_read(row["id"]))
        self.assertTrue(save_mock.called)

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_task_lifecycle(self, can_mock, save_mock, load_mock):
        row = p3_suite.create_task("Call client", priority="Высокий")
        self.assertEqual(row["status"], "Открыта")
        load_mock.return_value = [row]
        updated = p3_suite.update_task(row["id"], status="Готово")
        self.assertEqual(updated["status"], "Готово")

    def test_crm_scoring_is_deterministic(self):
        hot = p3_suite.enrich_lead({"name":"Иван","message":"Хочу купить кроссовки размер 42","phone":"+7000","product":"Nike"})
        cold = p3_suite.enrich_lead({"name":"Иван","message":"Просто смотрю"})
        self.assertGreater(hot["lead_score"], cold["lead_score"])
        self.assertEqual(hot["intent"], "Горячий")

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_agent_action_requires_approval(self, can_mock, save_mock, load_mock):
        row = p3_suite.queue_agent_action("create_task", {"title":"Follow-up"})
        self.assertEqual(row["status"], "pending_approval")
        self.assertTrue(save_mock.called)

if __name__ == "__main__":
    unittest.main()
