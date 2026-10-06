import os
import unittest
from unittest.mock import patch

import tbank_billing


class TBankBillingHardeningTests(unittest.TestCase):
    @patch.dict(os.environ, {"TBANK_RECEIPT_REQUIRED": "1", "TBANK_RECEIPT_TAXATION": "usn_income",
                             "TBANK_RECEIPT_TAX": "none", "TBANK_RECEIPT_EMAIL": "buyer@example.com"}, clear=False)
    def test_receipt_amount_matches_checkout_amount(self):
        receipt = tbank_billing._receipt_for_checkout("pro", 125000)
        self.assertEqual(receipt["Taxation"], "usn_income")
        self.assertEqual(receipt["Items"][0]["Amount"], 125000)
        self.assertEqual(receipt["Items"][0]["Price"], 125000)
        self.assertEqual(receipt["Payments"]["Electronic"], 125000)
        self.assertEqual(receipt["Items"][0]["PaymentObject"], "service")
        self.assertEqual(receipt["Email"], "buyer@example.com")

    @patch.dict(os.environ, {"TBANK_RECEIPT_REQUIRED": "1", "TBANK_RECEIPT_TAXATION": "usn_income",
                             "TBANK_RECEIPT_TAX": "none", "TBANK_RECEIPT_EMAIL": ""}, clear=False)
    def test_receipt_required_rejects_missing_customer_contact(self):
        with self.assertRaises(RuntimeError):
            tbank_billing._receipt_for_checkout("starter", 10000)


class BillingLifecycleSqlTests(unittest.TestCase):
    def test_refund_migration_revokes_matching_paid_access(self):
        sql = open("supabase/migrations/20261006090000_billing_refund_lifecycle.sql", encoding="utf-8").read()
        self.assertIn("deactivate_paid_subscription", sql)
        self.assertIn("current_sub.provider_payment_id is distinct from p_provider_payment_id", sql)
        self.assertIn("normalized_status in ('refunded','reversed','canceled','cancelled','rejected','deadline_expired')", sql)
        self.assertIn("plan = 'trial'", sql)
        self.assertIn("status = case", sql)

    def test_partial_refund_does_not_implicitly_revoke_full_access(self):
        sql = open("supabase/migrations/20261006090000_billing_refund_lifecycle.sql", encoding="utf-8").read()
        self.assertIn("('partial_refunded','partial_reversed')", sql)

    def test_tbank_notification_token_excludes_nested_data(self):
        import tbank_billing
        with patch.object(tbank_billing, "PASSWORD", "secret"):
            token = tbank_billing._token({
                "TerminalKey": "TBankTest",
                "PaymentId": "123",
                "Status": "CONFIRMED",
                "Data": {"tenant_id": "must-not-be-signed"},
                "Token": "ignored",
            })
        expected = __import__("hashlib").sha256(
            "secret123CONFIRMEDTBankTest".encode("utf-8")
        ).hexdigest()
        self.assertEqual(token, expected)


if __name__ == "__main__":
    unittest.main()
