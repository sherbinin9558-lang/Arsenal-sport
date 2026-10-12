import unittest


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

    def test_late_events_cannot_reactivate_terminal_checkout(self):
        sql = open("supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql", encoding="utf-8").read()
        self.assertIn("('refunded','reversed','canceled','cancelled','rejected','deadline_expired')", sql)
        self.assertIn("'reason', 'checkout_terminal'", sql)
        self.assertIn("if normalized_status in ('succeeded','confirmed') then", sql)
        self.assertNotIn("('succeeded','confirmed','authorized')", sql)

    def test_terminal_guard_preserves_service_role_only_rpc_access(self):
        sql = open("supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql", encoding="utf-8").read()
        self.assertIn("from public, anon, authenticated", sql)
        self.assertIn("to service_role", sql)


if __name__ == "__main__":
    unittest.main()
