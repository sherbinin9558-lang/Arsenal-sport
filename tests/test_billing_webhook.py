import hashlib
import json
import unittest
from unittest.mock import patch

import tbank_webhook


class FakeResponse:
    def __init__(self, payload=None, ok=True):
        self._payload = payload or {"ok": True}
        self.ok = ok
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class BillingWebhookTests(unittest.TestCase):
    @patch("tbank_webhook._supabase", return_value=("https://example.supabase.co", "test-service-key"))
    @patch("tbank_webhook.requests.post")
    def test_process_billing_event_uses_atomic_rpc_and_payload_hash(self, post, _supabase):
        post.return_value = FakeResponse({"ok": True, "duplicate": False})
        payload = {"id": "123", "status": "succeeded"}

        result = tbank_webhook._process_billing_event(
            "yookassa",
            "yookassa:payment.succeeded:123:succeeded",
            "123",
            "succeeded",
            "tenant-1",
            "pro",
            payload=payload,
        )

        self.assertFalse(result["duplicate"])
        args, request = post.call_args
        self.assertTrue(args[0].endswith("/rest/v1/rpc/process_billing_payment_event"))
        body = request["json"]
        expected_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(body["p_event_key"], "yookassa:payment.succeeded:123:succeeded")
        self.assertEqual(body["p_payload_hash"], expected_hash)
        self.assertEqual(body["p_tenant_id"], "tenant-1")
        self.assertEqual(body["p_plan"], "pro")
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-service-key")

    @patch("tbank_webhook._supabase", return_value=("https://example.supabase.co", "test-service-key"))
    @patch("tbank_webhook.requests.post")
    def test_process_billing_event_raises_on_rpc_failure(self, post, _supabase):
        post.return_value = FakeResponse({"message": "CHECKOUT_NOT_FOUND"}, ok=False)
        with self.assertRaises(RuntimeError):
            tbank_webhook._process_billing_event(
                "yookassa",
                "yookassa:payment.succeeded:123:succeeded",
                "123",
                "succeeded",
                "tenant-1",
                "starter",
            )

    def test_webhook_errors_do_not_expose_internal_exception_or_tenant(self):
        source = open("tbank_webhook.py", encoding="utf-8").read()
        self.assertNotIn('detail=f"Billing state transition failed: {exc}"', source)
        self.assertNotIn('        "tenant_id": tenant,', source)

    def test_only_yookassa_payment_webhook_route_is_registered(self):
        paths = {route.path for route in tbank_webhook.app.routes}
        self.assertIn("/webhooks/yookassa", paths)
        self.assertNotIn("/webhooks/tbank/payment-status", paths)

    @patch("tbank_webhook._checkout_by_provider_payment", return_value={"tenant_id": "tenant-1", "plan": "pro"})
    @patch("tbank_webhook._save_checkout")
    def test_recovery_uses_provider_metadata_and_persists_checkout(self, save_checkout, lookup):
        payment = {
            "id": "payment-recovery",
            "status": "succeeded",
            "amount": {"value": "990.00", "currency": "RUB"},
            "metadata": {
                "tenant_id": "tenant-1", "plan": "pro", "checkout_id": "checkout-1",
                "expected_amount": "990.00", "expected_currency": "RUB",
            },
        }
        result = tbank_webhook._recover_checkout_from_provider(payment)
        save_checkout.assert_called_once_with("tenant-1", "checkout-1", "payment-recovery", "pro", "990.00", "RUB")
        self.assertEqual(result["tenant_id"], "tenant-1")

    @patch("tbank_webhook._save_checkout")
    def test_recovery_rejects_provider_amount_mismatch(self, save_checkout):
        payment = {
            "id": "payment-mismatch", "status": "succeeded",
            "amount": {"value": "1.00", "currency": "RUB"},
            "metadata": {
                "tenant_id": "tenant-1", "plan": "pro", "checkout_id": "checkout-1",
                "expected_amount": "990.00", "expected_currency": "RUB",
            },
        }
        with self.assertRaises(tbank_webhook.HTTPException) as raised:
            tbank_webhook._recover_checkout_from_provider(payment)
        self.assertEqual(raised.exception.status_code, 422)
        save_checkout.assert_not_called()

    @patch("tbank_webhook._checkout_by_provider_payment", return_value=None)
    @patch("tbank_webhook._save_checkout", side_effect=RuntimeError("storage unavailable"))
    def test_recovery_returns_503_if_checkout_cannot_be_saved(self, save_checkout, lookup):
        payment = {
            "id": "payment-storage-failure", "status": "succeeded",
            "amount": {"value": "990.00", "currency": "RUB"},
            "metadata": {
                "tenant_id": "tenant-1", "plan": "pro", "checkout_id": "checkout-1",
                "expected_amount": "990.00", "expected_currency": "RUB",
            },
        }
        with self.assertRaises(tbank_webhook.HTTPException) as raised:
            tbank_webhook._recover_checkout_from_provider(payment)
        self.assertEqual(raised.exception.status_code, 503)
        lookup.assert_called_once_with("yookassa", "payment-storage-failure")

    def test_health_endpoint_is_present(self):
        paths = {route.path for route in tbank_webhook.app.routes}
        self.assertIn("/healthz", paths)
        self.assertIn("/readyz", paths)


if __name__ == "__main__":
    unittest.main()
