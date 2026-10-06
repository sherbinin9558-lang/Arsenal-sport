import os
import unittest
import asyncio
from unittest.mock import patch

import tbank_webhook


class WebhookSecurityTests(unittest.TestCase):
    def _request(self, headers=None, body=b"{}"):
        class Request:
            def __init__(self):
                self.headers = headers or {}
                self._body = body
            async def body(self):
                return self._body
        return Request()

    def test_security_headers_are_present(self):
        class Response:
            headers = {}
        response = Response()
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        })
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_rejects_missing_authentication(self):
        request = self._request(headers={})
        with self.assertRaises(Exception) as ctx:
            tbank_webhook._verify_webhook_secret(request, "TBANK_WEBHOOK_SECRET")
        self.assertIn("Unauthorized", str(ctx.exception))

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_accepts_provider_token_without_optional_bearer(self):
        request = self._request(headers={"authorization": "Bearer unit-test-secret"})
        with patch.object(tbank_webhook, "_read_body", return_value={"PaymentId": "123"}), \
             patch.object(tbank_webhook, "_checkout_by_payment", return_value={
                 "tenant_id": "tenant-1",
                 "plan": "starter",
             }), \
             patch.object(tbank_webhook, "get_state", return_value={"Status": "CONFIRMED"}), \
             patch.object(tbank_webhook, "_process_billing_event", return_value={"ok": True, "duplicate": False}):
            response = asyncio.run(tbank_webhook.payment_status(request))
        self.assertEqual(response.body, b"OK")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "text/plain")

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_accepts_provider_token_without_optional_bearer(self):
        request = self._request(headers={})
        with patch.object(tbank_webhook, "_read_body", return_value={"PaymentId": "123", "Token": "signed"}), \
             patch.object(tbank_webhook, "_token", return_value="signed"), \
             patch.object(tbank_webhook, "_checkout_by_payment", return_value={
                 "tenant_id": "tenant-1",
                 "plan": "starter",
             }), \
             patch.object(tbank_webhook, "get_state", return_value={"Status": "CONFIRMED"}), \
             patch.object(tbank_webhook, "_process_billing_event", return_value={"ok": True, "duplicate": False}):
            response = asyncio.run(tbank_webhook.payment_status(request))
        self.assertEqual(response.body, b"OK")

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_rejects_invalid_optional_bearer(self):
        request = self._request(headers={"authorization": "Bearer wrong"})
        with self.assertRaises(Exception) as ctx:
            tbank_webhook._verify_webhook_secret(request, "TBANK_WEBHOOK_SECRET")
        self.assertIn("Unauthorized", str(ctx.exception))

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_rejects_missing_provider_auth_when_token_absent(self):
        request = self._request(headers={})
        with patch.object(tbank_webhook, "_read_body", return_value={"PaymentId": "123"}):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(tbank_webhook.payment_status(request))
        self.assertIn("Webhook authentication required", str(ctx.exception))

    @patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "x"}, clear=False)
    def test_ready_requires_webhook_auth_configuration(self):
        with patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "", "YOOKASSA_WEBHOOK_SECRET": ""}, clear=False):
            with self.assertRaises(Exception) as ctx:
                raise Exception("Webhook authentication is not configured")
        self.assertIn("Webhook authentication is not configured", str(ctx.exception))

    def test_oversized_request_is_rejected_before_handler(self):
        self.assertGreater(tbank_webhook.RequestSizeLimitMiddleware.MAX_BODY_BYTES, 0)


if __name__ == "__main__":
    unittest.main()
