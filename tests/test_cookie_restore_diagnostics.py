"""Regression tests for cookie-restore timing and outcome diagnostics."""

import unittest
from unittest.mock import patch

import saas_core


class CookieRestoreDiagnosticsTests(unittest.TestCase):
    def test_success_records_total_timings_and_restored_outcome(self):
        with (
            patch.object(saas_core, "_read_refresh_token", return_value="refresh-token"),
            patch.object(saas_core, "refresh_session", return_value={"access_token": "access", "refresh_token": "rotated", "user": {"id": "u", "email": "e"}}),
            patch.object(saas_core, "_establish_session", return_value=True),
            patch.object(saas_core, "_record_auth_timing") as timing,
            patch.object(saas_core, "_record_auth_outcome") as outcome,
        ):
            self.assertTrue(saas_core._restore_session_from_cookie())

        operations = [call.args[0] for call in timing.call_args_list]
        self.assertIn("cookie_read", operations)
        self.assertIn("establish_session_total", operations)
        self.assertIn("cookie_restore_total", operations)
        outcome.assert_called_once_with("cookie_restore", "restored")

    def test_refresh_error_records_sanitized_outcome(self):
        error = saas_core.SupabaseRequestError("private backend detail", 503)
        with (
            patch.object(saas_core, "_read_refresh_token", return_value="refresh-token"),
            patch.object(saas_core, "refresh_session", side_effect=error),
            patch.object(saas_core, "_record_auth_timing") as timing,
            patch.object(saas_core, "_record_auth_outcome") as outcome,
        ):
            self.assertFalse(saas_core._restore_session_from_cookie())

        self.assertEqual(outcome.call_args.args, ("cookie_restore", "supabase_request_error"))
        self.assertNotIn("private backend detail", str(outcome.call_args))
        operations = [call.args[0] for call in timing.call_args_list]
        self.assertIn("establish_session_total", operations)
        self.assertIn("cookie_restore_total", operations)

    def test_unexpected_error_records_allowlisted_outcome(self):
        with (
            patch.object(saas_core, "_read_refresh_token", return_value="refresh-token"),
            patch.object(saas_core, "refresh_session", side_effect=RuntimeError("secret detail")),
            patch.object(saas_core, "_record_auth_timing"),
            patch.object(saas_core, "_record_auth_outcome") as outcome,
        ):
            self.assertFalse(saas_core._restore_session_from_cookie())

        outcome.assert_called_once_with("cookie_restore", "unexpected_error")
        self.assertNotIn("secret detail", str(outcome.call_args))


if __name__ == "__main__":
    unittest.main()
