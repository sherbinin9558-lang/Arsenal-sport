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

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "x",
        "YOO_KASSA_SHOP_ID": "",
        "YOO_KASSA_SECRET_KEY": "",
    }, clear=False)
    def test_ready_requires_provider_configuration(self):
        with self.assertRaises(Exception) as ctx:
            asyncio.run(tbank_webhook.readyz())
        self.assertEqual(getattr(ctx.exception, "status_code", None), 503)
        self.assertIn("YooKassa provider configuration", str(ctx.exception))

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "x",
        "YOO_KASSA_SHOP_ID": "shop",
        "YOO_KASSA_SECRET_KEY": "secret",
    }, clear=False)
    def test_ready_accepts_yookassa_configuration(self):
        result = asyncio.run(tbank_webhook.readyz())
        self.assertTrue(result["ok"])
        self.assertEqual(result["yookassa"], "configured")
        self.assertNotIn("tbank", result)

    @patch.dict(os.environ, {"YOOKASSA_WEBHOOK_SECRET": "yoo-secret"}, clear=False)
    def test_yookassa_rejects_wrong_optional_bearer(self):
        request = self._request(headers={"authorization": "Bearer wrong-secret"})
        with self.assertRaises(Exception) as ctx:
            asyncio.run(tbank_webhook.yookassa_payment_status(request))
        self.assertEqual(getattr(ctx.exception, "status_code", None), 401)

    def test_oversized_request_is_rejected_before_handler(self):
        self.assertGreater(tbank_webhook.RequestSizeLimitMiddleware.MAX_BODY_BYTES, 0)

    def test_chunked_oversized_request_is_rejected(self):
        async def run():
            sent = []
            chunks = [
                {"type": "http.request", "body": b"x" * (tbank_webhook.RequestSizeLimitMiddleware.MAX_BODY_BYTES // 2), "more_body": True},
                {"type": "http.request", "body": b"y" * (tbank_webhook.RequestSizeLimitMiddleware.MAX_BODY_BYTES // 2 + 1), "more_body": False},
            ]
            async def receive():
                return chunks.pop(0)
            async def send(message):
                sent.append(message)
            async def downstream(scope, receive, send):
                await receive()
                await receive()
            middleware = tbank_webhook.RequestSizeLimitMiddleware(downstream)
            await middleware({"type": "http", "headers": []}, receive, send)
            return sent
        sent = asyncio.run(run())
        body = b"".join(m.get("body", b"") for m in sent)
        self.assertTrue(any(m.get("status") == 413 for m in sent))
        self.assertIn(b"Request too large", body)

    @patch.dict(os.environ, {"YOOKASSA_WEBHOOK_SECRET": "yoo-secret"}, clear=False)
    def test_yookassa_refund_event_uses_original_payment_id(self):
        request = self._request(headers={"authorization": "Bearer yoo-secret"})
        body = {
            "event": "refund.succeeded",
            "object": {"id": "refund-1", "payment_id": "payment-1"},
        }
        with patch.object(tbank_webhook, "_read_body", return_value=body), \
             patch.object(tbank_webhook, "get_refund", return_value={"status": "succeeded", "payment_id": "payment-1"}), \
             patch.object(tbank_webhook, "get_payment", return_value={"status": "succeeded", "amount": {"value": "990.00", "currency": "RUB"}}), \
             patch.object(tbank_webhook, "_checkout_by_provider_payment", return_value={
                 "tenant_id": "tenant-1", "plan": "starter", "expected_amount": "990.00", "expected_currency": "RUB"
             }), \
             patch.object(tbank_webhook, "_process_billing_event", return_value={"ok": True, "duplicate": False}) as process:
            response = asyncio.run(tbank_webhook.yookassa_payment_status(request))
        self.assertEqual(response["status"], "refunded")
        self.assertEqual(response["payment_id"], "payment-1")
        self.assertEqual(process.call_args.args[2], "payment-1")
        self.assertEqual(process.call_args.args[3], "refunded")



if __name__ == "__main__":
    unittest.main()
