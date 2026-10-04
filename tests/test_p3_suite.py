import unittest
from unittest.mock import patch

import p3_suite


class TestP3Suite(unittest.TestCase):
    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_notification_lifecycle(self, can_mock, save_mock, load_mock):
        row = p3_suite.create_notification("Test", "Body")
        self.assertFalse(row["read"])
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

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_generated_ids_do_not_collide(self, can_mock, save_mock, load_mock):
        a = p3_suite.create_notification("A", "A")
        b = p3_suite.create_notification("B", "B")
        self.assertNotEqual(a["id"], b["id"])

    @patch("p3_suite.data_load", return_value=[
        {"id": "t1", "status": "Открыта", "due_date": "2000-01-01"},
        {"id": "t2", "status": "Готово", "due_date": "2000-01-01"},
    ])
    def test_task_metrics_calculates_overdue(self, load_mock):
        metrics = p3_suite.task_metrics()
        self.assertEqual(metrics["overdue"], 1)


    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_agent_payload_is_validated_and_expiry_is_set(self, can_mock, save_mock, load_mock):
        row = p3_suite.queue_agent_action("create_task", {"title": "Follow-up", "priority": "Высокий"})
        self.assertEqual(row["status"], "pending_approval")
        self.assertTrue(row.get("expires_at"))
        with self.assertRaises(ValueError):
            p3_suite.queue_agent_action("create_task", {"title": "x", "forbidden": "y"})

    def test_crm_insights_reports_funnel_and_duplicates(self):
        leads = [
            {"id":"1","name":"A","contact":"same","message":"Хочу купить", "product":"Кроссовки","status":"Заказ оформлен"},
            {"id":"2","name":"B","contact":"same","message":"Цена?", "product":"Кроссовки","status":"Новый"},
            {"id":"3","name":"C","contact":"c","message":"Просто смотрю","status":"В работе"},
        ]
        result = p3_suite.crm_insights(leads)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["duplicate_contacts"], 1)
        self.assertGreaterEqual(result["conversion_rate"], 33)

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_instagram_lifecycle_and_schedule(self, can_mock, save_mock, load_mock):
        row = p3_suite.queue_instagram_draft("Новый пост", scheduled_at="2030-01-01T10:00:00Z", record_id="same")
        self.assertEqual(row["status"], "Черновик")
        load_mock.side_effect = [
            [dict(row)],
            [{**row, "status": "На проверке"}],
            [{**row, "status": "Одобрено"}],
            [{**row, "status": "Запланировано", "scheduled_at": "2030-01-01T10:00:00Z"}],
            [{**row, "status": "Запланировано", "scheduled_at": "2030-01-01T10:00:00Z"}],
        ]
        updated = p3_suite.update_instagram_draft(row["id"], status="На проверке")
        self.assertEqual(updated["status"], "На проверке")
        # Explicit approval transition: Черновик -> На проверке -> Одобрено.
        updated = p3_suite.update_instagram_draft(row["id"], status="Одобрено")
        self.assertEqual(updated["status"], "Одобрено")
        updated = p3_suite.update_instagram_draft(row["id"], status="Запланировано", scheduled_at="2030-01-01T10:00:00Z")
        self.assertEqual(updated["status"], "Запланировано")
        with self.assertRaises(ValueError):
            p3_suite.update_instagram_draft(row["id"], status="Опубликовано")
        with self.assertRaises(ValueError):
            p3_suite.update_instagram_draft(row["id"], status="Черновик")

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    @patch("p3_suite.current_role", return_value="manager")
    def test_approval_records_actor_and_executes_safely(self, role_mock, can_mock, save_mock, load_mock):
        row = p3_suite.queue_agent_action("create_notification", {"title": "T", "body": "B"})
        load_mock.return_value = [row]
        approved = p3_suite.approve_agent_action(row["id"], execute=False)
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approved_by_role"], "manager")

    @patch("p3_suite.data_load", return_value=[])
    @patch("p3_suite.data_save")
    @patch("p3_suite.can", return_value=True)
    def test_instagram_requires_timezone_and_valid_transition(self, can_mock, save_mock, load_mock):
        row = p3_suite.queue_instagram_draft("Post")
        load_mock.return_value = [row]
        with self.assertRaises(ValueError):
            p3_suite.update_instagram_draft(row["id"], scheduled_at="2030-01-01T10:00:00")

if __name__ == "__main__":
    unittest.main()
