import unittest

from max_operator import execute_write


class MaxWriteBoundaryTests(unittest.TestCase):
    def test_write_requires_confirmation(self):
        called = []
        result = execute_write("quick_content_plan", False, lambda: called.append(True))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "not_approved")
        self.assertEqual(called, [])

    def test_approved_write_executes(self):
        called = []
        result = execute_write("quick_content_plan", True, lambda: called.append(True) or 7)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], 7)
        self.assertEqual(called, [True])


if __name__ == "__main__":
    unittest.main()
