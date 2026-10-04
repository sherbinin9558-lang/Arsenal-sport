import ast
from pathlib import Path
import unittest


class TelegramReelsAuthRegressionTest(unittest.TestCase):
    def test_reels_uses_authenticated_token_helper(self):
        source = Path("app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "publish_reel_to_telegram")
        calls = [node.func.id for node in ast.walk(fn) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertIn("_telegram_auth_token", calls)
        self.assertNotIn("_telegram_token", calls)


if __name__ == "__main__":
    unittest.main()
