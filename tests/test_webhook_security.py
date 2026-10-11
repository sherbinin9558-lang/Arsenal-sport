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

    def test_read_body_rejects_non_object_json(self):
        class JsonRequest:
            def __init__(self, payload):
                self.payload = payload

            async def json(self):
                return self.payload

        for payload in ([], "string", 42, None):
            with self.subTest(payload=payload):
                with self.assertRaises(Exception) as ctx:
                    asyncio.run(tbank_webhook._read_body(JsonRequest(payload)))
                self.assertEqual(getattr(ctx.exception, "status_code", None), 400)
                self.assertIn("JSON object required", str(ctx.exception))

    def test_read_body_accepts_json_object(self):
        class JsonRequest:
            async def json(self):
                return {"PaymentId": "123"}

        self.assertEqual(asyncio.run(tbank_webhook._read_body(JsonRequest())), {"PaymentId": "123"})

    def test_security_headers_are_applied_by_real_middleware(self):
        async def run():
            from starlette.requests import Request
            from starlette.responses import PlainTextResponse

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "https",
                "path": "/healthz",
                "raw_path": b"/healthz",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 443),
            }
            request = Request(scope, receive=receive)

            async def call_next(_request):
                return PlainTextResponse("ok")

            middleware = tbank_webhook.SecurityHeadersMiddleware(tbank_webhook.app)
            return await middleware.dispatch(request, call_next)

        response = asyncio.run(run())
        expected = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
        for header, value in expected.items():
            with self.subTest(header=header):
                self.assertEqual(response.headers.get(header), value)

    @patch.dict(os.environ, {"TBANK_WEBHOOK_SECRET": "unit-test-secret"}, clear=False)
    def test_tbank_accepts_configured_bearer_secret(self):
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

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "x",
        "TBANK_TERMINAL_KEY": "",
        "TBANK_PASSWORD": "",
        "YOOKASSA_WEBHOOK_SECRET": "",
    }, clear=False)
    def test_ready_requires_provider_configuration(self):
        with self.assertRaises(Exception) as ctx:
            asyncio.run(tbank_webhook.readyz())
        self.assertEqual(getattr(ctx.exception, "status_code", None), 503)
        self.assertIn("provider authentication", str(ctx.exception))

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "x",
        "TBANK_TERMINAL_KEY": "terminal",
        "TBANK_PASSWORD": "password",
        "TBANK_WEBHOOK_SECRET": "",
    }, clear=False)
    def test_ready_accepts_tbank_provider_configuration(self):
        result = asyncio.run(tbank_webhook.readyz())
        self.assertTrue(result["ok"])
        self.assertEqual(result["tbank"], "configured")
        self.assertEqual(result["yookassa"], "disabled")

    @patch.dict(os.environ, {"YOOKASSA_WEBHOOK_SECRET": "yoo-secret"}, clear=False)
    def test_yookassa_requires_configured_bearer(self):
        request = self._request(headers={})
        with self.assertRaises(Exception) as ctx:
            asyncio.run(tbank_webhook.yookassa_payment_status(request))
        self.assertEqual(getattr(ctx.exception, "status_code", None), 401)

    def test_oversized_request_is_rejected_before_handler(self):
        async def run():
            sent = []
            downstream_called = False

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                sent.append(message)

            async def downstream(scope, receive, send):
                nonlocal downstream_called
                downstream_called = True

            middleware = tbank_webhook.RequestSizeLimitMiddleware(downstream)
            await middleware(
                {"type": "http", "headers": [
                    (b"content-length", str(middleware.MAX_BODY_BYTES + 1).encode("ascii"))
                ]},
                receive,
                send,
            )
            return sent, downstream_called

        sent, downstream_called = asyncio.run(run())
        self.assertFalse(downstream_called)
        self.assertTrue(any(message.get("status") == 413 for message in sent))
        body = b"".join(message.get("body", b"") for message in sent)
        self.assertIn(b"Request too large", body)

    def test_invalid_content_length_is_rejected_before_handler(self):
        async def run():
            sent = []
            downstream_called = False

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                sent.append(message)

            async def downstream(scope, receive, send):
                nonlocal downstream_called
                downstream_called = True

            middleware = tbank_webhook.RequestSizeLimitMiddleware(downstream)
            await middleware(
                {"type": "http", "headers": [(b"content-length", b"not-a-number")]},
                receive,
                send,
            )
            return sent, downstream_called

        sent, downstream_called = asyncio.run(run())
        self.assertFalse(downstream_called)
        self.assertTrue(any(message.get("status") == 400 for message in sent))
        body = b"".join(message.get("body", b"") for message in sent)
        self.assertIn(b"Invalid Content-Length", body)

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
             patch.object(tbank_webhook, "get_payment", return_value={"status": "succeeded"}), \
             patch.object(tbank_webhook, "_checkout_by_provider_payment", return_value={
                 "tenant_id": "tenant-1", "plan": "starter"
             }), \
             patch.object(tbank_webhook, "_process_billing_event", return_value={"ok": True, "duplicate": False}) as process:
            response = asyncio.run(tbank_webhook.yookassa_payment_status(request))
        self.assertEqual(response["status"], "refunded")
        self.assertEqual(response["payment_id"], "payment-1")
        self.assertEqual(process.call_args.args[2], "payment-1")
        self.assertEqual(process.call_args.args[3], "refunded")



if __name__ == "__main__":
    unittest.main()
