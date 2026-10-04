import os
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    import tbank_webhook
    HAS_WEBHOOK_DEPS = True
except Exception:  # fastapi/httpx not installed
    HAS_WEBHOOK_DEPS = False

try:
    import telegram_bot
    HAS_BOT = True
except Exception:
    HAS_BOT = False


@unittest.skipUnless(HAS_WEBHOOK_DEPS, "fastapi and httpx are required")
class TbankWebhookAuthTests(unittest.TestCase):
    PATH = "/webhooks/tbank/payment-status"

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "s3cret"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(tbank_webhook.app)

    def test_missing_or_wrong_secret_is_rejected(self):
        self.assertEqual(self.client.post(self.PATH, json={"PaymentId": "1"}).status_code, 401)
        wrong = {"authorization": "Bearer nope"}
        self.assertEqual(self.client.post(self.PATH, json={"PaymentId": "1"}, headers=wrong).status_code, 401)

    def test_bad_signature_is_rejected_even_with_non_ascii_value(self):
        right = {"authorization": "Bearer s3cret"}
        for token in ("badtoken", "абв"):
            response = self.client.post(self.PATH, json={"PaymentId": "1", "Token": token}, headers=right)
            self.assertEqual(response.status_code, 401, token)


@unittest.skipUnless(HAS_BOT, "telegram_bot could not be imported")
class TelegramBotLoopTests(unittest.TestCase):
    def test_polling_error_waits_instead_of_spinning(self):
        class Stop(Exception):
            pass

        sleeps = []

        def fake_sleep(seconds):
            sleeps.append(seconds)
            raise Stop()

        with mock.patch.object(telegram_bot, "validate_config", lambda: None), \
             mock.patch.object(telegram_bot, "tg", side_effect=RuntimeError("401 Unauthorized")), \
             mock.patch.object(telegram_bot.time, "sleep", fake_sleep):
            with self.assertRaises(Stop):
                telegram_bot.main()
        self.assertEqual(sleeps, [5])

    def test_admin_notification_failure_is_not_fatal(self):
        with mock.patch.object(telegram_bot, "ADMIN_CHAT_ID", "1"), \
             mock.patch.object(telegram_bot, "send", side_effect=RuntimeError("down")):
            telegram_bot.notify_admin("test")  # must not raise


if __name__ == "__main__":
    unittest.main()
