import unittest
from unittest.mock import patch

import tbank_billing


class FakeResponse:
    def __init__(self, payload=None, ok=True):
        self.payload = payload or {"Success": True, "PaymentId": "pay-123"}
        self.ok = ok
        self.text = ""

    def json(self):
        return self.payload


class TBankCheckoutPersistenceTests(unittest.TestCase):
    @patch.object(tbank_billing, "_save_checkout")
    @patch.object(tbank_billing.requests, "post")
    @patch.object(tbank_billing, "configured", return_value=True)
    @patch.object(tbank_billing, "plan_price", return_value=990.0)
    @patch.object(tbank_billing.time, "sleep")
    def test_checkout_retries_durable_save_after_provider_success(
        self, sleep, _price, _configured, post, save_checkout
    ):
        post.return_value = FakeResponse()
        save_checkout.side_effect = [RuntimeError("temporary"), None]

        result = tbank_billing.create_checkout("pro", "tenant-1")

        self.assertEqual(result["PaymentId"], "pay-123")
        self.assertEqual(save_checkout.call_count, 2)
        sleep.assert_called_once_with(0.5)


if __name__ == "__main__":
    unittest.main()
