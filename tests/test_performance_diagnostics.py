import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "saas_core.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def function_node(name):
    return next(
        node for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


class PerformanceDiagnosticsSafetyTests(unittest.TestCase):
    def test_request_timing_uses_monotonic_clock_and_finally(self):
        node = function_node("_request")
        calls = [
            call for call in ast.walk(node)
            if isinstance(call, ast.Call)
        ]
        call_names = {
            call.func.id if isinstance(call.func, ast.Name)
            else call.func.attr if isinstance(call.func, ast.Attribute)
            else ""
            for call in calls
        }
        self.assertIn("perf_counter", call_names)
        self.assertTrue(
            any(isinstance(item, ast.Try) and item.finalbody for item in ast.walk(node)),
            "_request must log timings for both successful and failed HTTP requests",
        )

    def test_endpoint_group_does_not_return_raw_paths(self):
        node = function_node("_perf_endpoint_group")
        returns = [
            item.value for item in ast.walk(node)
            if isinstance(item, ast.Return) and isinstance(item.value, ast.Constant)
        ]
        labels = {item.value for item in returns if isinstance(item.value, str)}
        self.assertTrue({"auth", "rest_rpc", "rest_table", "other"}.issubset(labels))
        self.assertFalse(any("/" in label or "?" in label for label in labels))

    def test_diagnostic_log_contains_only_allowlisted_fields(self):
        node = function_node("_request")
        printed = [
            item for item in ast.walk(node)
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id == "print"
        ]
        self.assertEqual(len(printed), 1, "Expected one bounded diagnostic log statement")
        rendered = ast.unparse(printed[0])
        for safe_field in ("PERF_DIAG", "method", "endpoint", "elapsed_ms", "status"):
            self.assertIn(safe_field, rendered)
        for forbidden in ("token", "headers", "response", "tenant_id", "email", "url"):
            self.assertNotIn(forbidden, rendered.lower())

    def test_no_request_query_or_response_body_is_logged(self):
        node = function_node("_request")
        printed = [
            item for item in ast.walk(node)
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id == "print"
        ]
        rendered = ast.unparse(printed[0]).lower()
        self.assertNotIn("r.text", rendered)
        self.assertNotIn("r.json", rendered)
        self.assertNotIn("kwargs", rendered)
        self.assertNotIn("path}", rendered)


if __name__ == "__main__":
    unittest.main()
