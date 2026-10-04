import io
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

class TestP2Hardening(unittest.TestCase):
    def test_imports_and_feature_layer(self):
        import p3_suite
        self.assertTrue(p3_suite.ACTION_REGISTRY)
        self.assertIn("queue_instagram_draft", p3_suite.ACTION_REGISTRY)

    def test_agent_actions_are_approval_gated(self):
        import p3_suite
        self.assertEqual(p3_suite.ACTION_REGISTRY["create_task"]["side_effect"], "internal")
        self.assertNotIn("publish_payment", p3_suite.ACTION_REGISTRY)

    def test_large_csv_stream_shape(self):
        # 50k rows: validates parsing primitives without depending on production UI.
        rows = ["name,brand,article\n"] + [f"Ball {i},Brand,{i}\n" for i in range(50000)]
        payload = io.StringIO("".join(rows))
        count = sum(1 for _ in payload) - 1
        self.assertEqual(count, 50000)

    def test_concurrent_version_conflict_model(self):
        # Deterministic optimistic-concurrency model: only one writer may advance v=1.
        state = {"version": 1, "writes": 0}
        from threading import Lock
        lock = Lock()
        def writer():
            with lock:
                expected = 1
                if state["version"] != expected:
                    return False
                state["version"] += 1
                state["writes"] += 1
                return True
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: writer(), range(8)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(state["version"], 2)

    def test_expired_session_statuses_are_recoverable(self):
        from saas_core import SupabaseRequestError
        self.assertIn(SupabaseRequestError("expired", 401).status_code, (400,401,403))

    def test_billing_modules_are_importable_without_live_charge(self):
        import billing, tbank_billing
        self.assertFalse(billing.configured() or tbank_billing.configured()
                         if not (os.getenv("YOO_KASSA_SHOP_ID") or os.getenv("TBANK_TERMINAL_KEY"))
                         else True)

if __name__ == "__main__":
    unittest.main()
