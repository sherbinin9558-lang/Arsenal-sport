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

    def test_tbank_webhook_errors_do_not_expose_exception_or_tenant(self):
        from fastapi import HTTPException
        from types import SimpleNamespace
        request = SimpleNamespace(headers={})
        payload = {"PaymentId": "payment-123", "Token": "valid-token"}

        with patch.dict("os.environ", {"TBANK_WEBHOOK_SECRET": ""}, clear=False), \
             patch.object(tbank_webhook, "_read_body", return_value=payload), \
             patch.object(tbank_webhook, "_token", return_value="valid-token"), \
             patch.object(tbank_webhook, "_checkout_by_payment", return_value={
                 "tenant_id": "tenant-sensitive-987", "plan": "pro"
             }), \
             patch.object(tbank_webhook, "get_state", return_value={"Status": "CONFIRMED"}), \
             patch.object(tbank_webhook, "_process_billing_event", side_effect=RuntimeError("INTERNAL-DB-SECRET")):
            with self.assertRaises(HTTPException) as ctx:
                import asyncio
                asyncio.run(tbank_webhook.payment_status(request))

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail, "Billing state transition failed")
        self.assertNotIn("INTERNAL-DB-SECRET", str(ctx.exception.detail))
        self.assertNotIn("tenant-sensitive-987", str(ctx.exception.detail))

    def test_yookassa_webhook_errors_do_not_expose_exception_or_tenant(self):
        from fastapi import HTTPException
        from types import SimpleNamespace
        import asyncio
        request = SimpleNamespace(headers={"authorization": "Bearer unit-yoo-secret"})
        payload = {"event": "payment.succeeded", "object": {"id": "payment-456"}}

        with patch.dict("os.environ", {"YOOKASSA_WEBHOOK_SECRET": "unit-yoo-secret"}, clear=False), \
             patch.object(tbank_webhook, "_read_body", return_value=payload), \
             patch.object(tbank_webhook, "get_payment", return_value={"status": "succeeded"}), \
             patch.object(tbank_webhook, "_checkout_by_provider_payment", return_value={
                 "tenant_id": "tenant-sensitive-654", "plan": "starter"
             }), \
             patch.object(tbank_webhook, "_process_billing_event", side_effect=RuntimeError("INTERNAL-YOO-SECRET")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(tbank_webhook.yookassa_payment_status(request))

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail, "Billing state transition failed")
        self.assertNotIn("INTERNAL-YOO-SECRET", str(ctx.exception.detail))
        self.assertNotIn("tenant-sensitive-654", str(ctx.exception.detail))

    def test_health_endpoint_is_present(self):
        paths = {route.path for route in tbank_webhook.app.routes}
        self.assertIn("/healthz", paths)
        self.assertIn("/readyz", paths)


if __name__ == "__main__":
    unittest.main()
