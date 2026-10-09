import unittest
from unittest.mock import Mock, patch

import billing


class YooKassaSBPCheckoutTests(unittest.TestCase):
    @patch.object(billing, "_save_checkout")
    @patch.object(billing.requests, "post")
    @patch.object(billing, "_cfg", return_value="configured")
    @patch.object(billing, "configured", return_value=True)
    @patch.object(billing, "plan_price", return_value=990.0)
    def test_sbp_checkout_requests_sbp_and_does_not_save_payment_method(
        self, _price, _configured, _cfg, post, save_checkout
    ):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "id": "payment-123",
            "confirmation": {"confirmation_url": "https://yookassa.example/checkout"},
        }
        post.return_value = response

        result = billing.create_checkout("pro", "tenant-1", payment_method="sbp")

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["payment_method_data"], {"type": "sbp"})
        self.assertFalse(payload["save_payment_method"])
        self.assertEqual(payload["metadata"]["tenant_id"], "tenant-1")
        self.assertEqual(result["id"], "payment-123")
        save_checkout.assert_called_once_with("tenant-1", payload["metadata"]["checkout_id"], "payment-123", "pro")

    @patch.object(billing, "_save_checkout")
    @patch.object(billing.requests, "post")
    @patch.object(billing, "_cfg", return_value="configured")
    @patch.object(billing, "configured", return_value=True)
    @patch.object(billing, "plan_price", return_value=990.0)
    def test_default_checkout_keeps_provider_payment_method_selection(
        self, _price, _configured, _cfg, post, _save_checkout
    ):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "id": "payment-456",
            "confirmation": {"confirmation_url": "https://yookassa.example/checkout"},
        }
        post.return_value = response

        billing.create_checkout("pro", "tenant-1")

        payload = post.call_args.kwargs["json"]
        self.assertNotIn("payment_method_data", payload)
        self.assertFalse(payload["save_payment_method"])

    def test_rejects_unknown_payment_method(self):
        with self.assertRaises(ValueError):
            billing.create_checkout("pro", "tenant-1", payment_method="qr")

    @patch.object(billing, "configured", return_value=True)
    @patch.object(billing, "plan_price", return_value=990.0)
    @patch.object(billing, "_cfg", return_value="configured")
    @patch.object(billing.requests, "post")
    def test_provider_error_details_are_not_exposed(self, post, _cfg, _price, _configured):
        response = Mock()
        response.ok = False
        response.json.return_value = {"description": "private provider diagnostic"}
        response.text = "private provider diagnostic"
        post.return_value = response

        with self.assertRaises(RuntimeError) as raised:
            billing.create_checkout("pro", "tenant-1", payment_method="sbp")

        self.assertNotIn("private provider diagnostic", str(raised.exception))
        self.assertIn("ЮKassa", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
