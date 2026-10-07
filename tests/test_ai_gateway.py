import unittest

from ai_gateway import AIUsage, estimate_text_tokens


class AIGatewayTests(unittest.TestCase):
    def test_token_estimate_is_deterministic(self):
        self.assertEqual(estimate_text_tokens(""), 0)
        self.assertEqual(estimate_text_tokens("abcd"), 1)
        self.assertEqual(estimate_text_tokens("abcde"), 2)

    def test_usage_cost_delegates_to_shared_model(self):
        usage = AIUsage(
            operation="test",
            provider="local",
            model="deterministic",
            input_tokens=1000,
            output_tokens=500,
        )
        self.assertGreaterEqual(usage.estimated_cost_rub, 0.0)


if __name__ == "__main__":
    unittest.main()
