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
        payload = {"PaymentId": "123", "Status": "CONFIRMED"}

        result = tbank_webhook._process_billing_event(
            "tbank",
            "tbank:123:confirmed",
            "123",
            "CONFIRMED",
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
        self.assertEqual(body["p_event_key"], "tbank:123:confirmed")
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

    def test_health_endpoint_is_present(self):
        paths = {route.path for route in tbank_webhook.app.routes}
        self.assertIn("/healthz", paths)
        self.assertIn("/readyz", paths)


if __name__ == "__main__":
    unittest.main()
