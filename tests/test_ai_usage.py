import unittest

from ai_usage import estimate_cost_rub, format_usage_summary_caption


class AiUsageTests(unittest.TestCase):
    def test_zero_cost_for_free_first_defaults(self):
        self.assertEqual(estimate_cost_rub(1000, 2000), 0.0)

    def test_cost_estimation_uses_token_rates(self):
        import os
        old_in = os.environ.get("AI_INPUT_RUB_PER_1K")
        old_out = os.environ.get("AI_OUTPUT_RUB_PER_1K")
        os.environ["AI_INPUT_RUB_PER_1K"] = "0.50"
        os.environ["AI_OUTPUT_RUB_PER_1K"] = "1.25"
        try:
            self.assertAlmostEqual(estimate_cost_rub(2000, 4000), 6.0)
        finally:
            if old_in is None:
                os.environ.pop("AI_INPUT_RUB_PER_1K", None)
            else:
                os.environ["AI_INPUT_RUB_PER_1K"] = old_in
            if old_out is None:
                os.environ.pop("AI_OUTPUT_RUB_PER_1K", None)
            else:
                os.environ["AI_OUTPUT_RUB_PER_1K"] = old_out


    def test_usage_caption_distinguishes_estimate_from_provider_bill(self):
        caption = format_usage_summary_caption({"requests": 7, "cost_rub": 1.25}, 30)
        self.assertIn("операции за 30 дней: 7", caption)
        self.assertIn("1.2500 ₽", caption)
        self.assertIn("не счёт", caption)


if __name__ == "__main__":
    unittest.main()
