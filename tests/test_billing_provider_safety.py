"""Regression tests for payment configuration and provider-error safety.

All HTTP calls are mocked: this suite must never create real payments.
"""
import unittest
from unittest.mock import patch

import billing
import tbank_billing


class FakeResponse:
    def __init__(self, payload, ok=True, text=None):
        self._payload = payload
        self.ok = ok
        self.text = text if text is not None else str(payload)

    def json(self):
        return self._payload


class BillingProviderSafetyTests(unittest.TestCase):
    def test_non_finite_and_non_positive_prices_are_rejected(self):
        for raw in ("nan", "NaN", "inf", "-inf", "0", "-10", "not-a-price", ""):
            with self.subTest(raw=raw), patch.object(billing, "_cfg", return_value=raw):
                self.assertEqual(billing.plan_price("starter"), 0.0)

    def test_unknown_plan_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Недопустимый тариф"):
            billing.plan_price("unknown")

    @patch.object(billing, "_save_checkout")
    @patch.object(billing.requests, "post")
    @patch.object(billing, "configured", return_value=True)
    @patch.object(billing, "_cfg")
    def test_saving_payment_method_is_disabled_by_default(self, cfg, _configured, post, save):
        values = {
            "SAAS_STARTER_PRICE": "100.00",
            "YOO_KASSA_SHOP_ID": "shop-test",
            "YOO_KASSA_SECRET_KEY": "secret-test",
            "SAAS_PUBLIC_URL": "https://example.test",
            "SUPABASE_SERVICE_ROLE_KEY": "service-test",
            "SUPABASE_URL": "https://example.supabase.co",
            "YOO_KASSA_SAVE_PAYMENT_METHOD": "",
        }
        cfg.side_effect = lambda name, default="": values.get(name, default)
        post.return_value = FakeResponse({
            "id": "payment-test",
            "confirmation": {"confirmation_url": "https://provider.example/checkout"},
        })
        billing.create_checkout("starter", "tenant-test")
        payload = post.call_args.kwargs["json"]
        self.assertFalse(payload["save_payment_method"])
        self.assertEqual(post.call_args.args[0], "https://api.yookassa.ru/v3/payments")
        save.assert_called_once()

    @patch.object(billing.requests, "post")
    @patch.object(billing, "configured", return_value=True)
    @patch.object(billing, "_cfg")
    def test_provider_error_does_not_leak_response_body(self, cfg, _configured, post):
        values = {
            "SAAS_STARTER_PRICE": "100.00",
            "YOO_KASSA_SHOP_ID": "shop-test",
            "YOO_KASSA_SECRET_KEY": "secret-test",
            "SAAS_PUBLIC_URL": "https://example.test",
            "SUPABASE_SERVICE_ROLE_KEY": "service-test",
            "SUPABASE_URL": "https://example.supabase.co",
        }
        cfg.side_effect = lambda name, default="": values.get(name, default)
        post.return_value = FakeResponse(
            {"description": "SECRET-INTERNAL-PROVIDER-DETAIL"}, ok=False,
            text="SECRET-INTERNAL-PROVIDER-DETAIL",
        )
        with self.assertRaises(RuntimeError) as ctx:
            billing.create_checkout("starter", "tenant-test")
        self.assertNotIn("SECRET-INTERNAL-PROVIDER-DETAIL", str(ctx.exception))
        self.assertIn("ЮKassa", str(ctx.exception))


    @patch.object(billing.requests, "get")
    @patch.object(billing, "configured", return_value=True)
    def test_payment_lookup_error_does_not_leak_provider_body(self, _configured, get):
        get.return_value = FakeResponse(
            {"description": "SECRET-PAYMENT-LOOKUP-DETAIL"}, ok=False,
            text="SECRET-PAYMENT-LOOKUP-DETAIL",
        )
        with self.assertRaises(RuntimeError) as ctx:
            billing.get_payment("payment-test")
        self.assertNotIn("SECRET-PAYMENT-LOOKUP-DETAIL", str(ctx.exception))

    @patch.object(billing.requests, "post")
    @patch.object(billing, "_cfg")
    def test_checkout_storage_error_does_not_leak_response_body(self, cfg, post):
        values = {
            "SUPABASE_SERVICE_ROLE_KEY": "service-test",
            "SUPABASE_URL": "https://example.supabase.co",
        }
        cfg.side_effect = lambda name, default="": values.get(name, default)
        post.return_value = FakeResponse(
            {"message": "SECRET-STORAGE-DETAIL"}, ok=False,
            text="SECRET-STORAGE-DETAIL",
        )
        with self.assertRaises(RuntimeError) as ctx:
            billing._save_checkout("tenant-test", "checkout-test", "payment-test", "starter")
        self.assertNotIn("SECRET-STORAGE-DETAIL", str(ctx.exception))


    def test_tbank_rejects_non_finite_and_unknown_plan_prices(self):
        with patch.object(tbank_billing, "_cfg", return_value="nan"):
            self.assertEqual(tbank_billing.plan_price("starter"), 0.0)
        with self.assertRaisesRegex(ValueError, "Недопустимый тариф"):
            tbank_billing.plan_price("unknown")

    @patch.object(tbank_billing.requests, "post")
    @patch.object(tbank_billing, "configured", return_value=True)
    @patch.object(tbank_billing, "plan_price", return_value=100.0)
    def test_tbank_checkout_error_does_not_leak_provider_body(self, _price, _configured, post):
        post.return_value = FakeResponse(
            {"Success": False, "Message": "SECRET-TBANK-PROVIDER-DETAIL"},
            ok=True,
            text="SECRET-TBANK-PROVIDER-DETAIL",
        )
        with self.assertRaises(RuntimeError) as ctx:
            tbank_billing.create_checkout("starter", "tenant-test")
        self.assertNotIn("SECRET-TBANK-PROVIDER-DETAIL", str(ctx.exception))

    @patch.object(tbank_billing.requests, "post")
    @patch.object(tbank_billing, "configured", return_value=True)
    def test_tbank_payment_state_error_does_not_leak_provider_body(self, _configured, post):
        post.return_value = FakeResponse(
            {"Success": False, "Message": "SECRET-TBANK-STATE-DETAIL"},
            ok=True,
            text="SECRET-TBANK-STATE-DETAIL",
        )
        with self.assertRaises(RuntimeError) as ctx:
            tbank_billing.get_state("payment-test")
        self.assertNotIn("SECRET-TBANK-STATE-DETAIL", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
