import unittest
from collections import defaultdict, deque
from unittest.mock import patch

import saas_core


class AuthHardeningTests(unittest.TestCase):
    def setUp(self):
        saas_core.st.session_state.clear()

    def test_auth_attempt_limit_blocks_sixth_attempt(self):
        with patch.object(saas_core, "_request", side_effect=saas_core.SupabaseRequestError("bad", 401)):
            for _ in range(5):
                with self.assertRaises(saas_core.SupabaseRequestError):
                    saas_core.sign_in("user@example.com", "bad")
            with self.assertRaisesRegex(saas_core.SupabaseRequestError, "Слишком много"):
                saas_core.sign_in("user@example.com", "bad")

    def test_successful_login_clears_attempt_history(self):
        with patch.object(saas_core, "_request", return_value={"access_token": "x"}):
            for _ in range(2):
                saas_core.sign_in("user@example.com", "good")
        self.assertEqual(saas_core.st.session_state.get(saas_core._AUTH_ATTEMPTS_KEY, {}).get("user@example.com"), None)

    def test_global_rate_limit_is_shared_across_sessions(self):
        saas_core._AUTH_GLOBAL_ATTEMPTS.clear()
        email = "shared@example.com"
        with patch.object(saas_core, "_client_fingerprint", return_value="203.0.113.10"):
            for _ in range(saas_core._AUTH_GLOBAL_LIMIT):
                saas_core._check_global_auth_attempt_limit(email)
            with self.assertRaisesRegex(saas_core.SupabaseRequestError, "Слишком много"):
                saas_core._check_global_auth_attempt_limit(email)

    def test_auth_error_is_generic(self):
        self.assertEqual(
            saas_core._safe_auth_error(saas_core.SupabaseRequestError("secret backend detail", 401)),
            "Не удалось выполнить вход. Проверьте email и пароль.",
        )
        self.assertEqual(
            saas_core._safe_auth_error(saas_core.SupabaseRequestError("backend detail", 429)),
            "Слишком много попыток входа. Повторите позже.",
        )


    def test_auth_bootstrap_accepts_restored_cookie_without_login_ui(self):
        with patch.object(saas_core, "_restore_session_from_cookie", return_value=True):
            self.assertTrue(saas_core._auth_bootstrap_gate())
        self.assertNotIn("_saas_auth_bootstrap_done", saas_core.st.session_state)

    def test_auth_bootstrap_waits_without_rendering_login_during_cookie_handshake(self):
        calls = {"restore": 0, "rerun": 0, "login": 0}

        def restore():
            calls["restore"] += 1
            return False

        def rerun():
            calls["rerun"] += 1

        with (patch.object(saas_core, "saas_enabled", return_value=True),
              patch.object(saas_core, "_restore_session_from_cookie", side_effect=restore),
              patch.object(saas_core.st, "rerun", side_effect=rerun),
              patch.object(saas_core.time, "sleep"),
              patch.object(saas_core, "login_ui", side_effect=lambda: calls.__setitem__("login", calls["login"] + 1))):
            saas_core.require_saas_access()

        self.assertGreater(calls["restore"], 0)
        self.assertGreater(calls["rerun"], 0)
        self.assertEqual(calls["login"], 0)
        self.assertFalse(saas_core.st.session_state.get("_saas_auth_bootstrap_done", False))

    def test_auth_bootstrap_timeout_releases_control_to_login(self):
        saas_core.st.session_state["_saas_auth_bootstrap_started_at"] = 100.0
        saas_core.st.session_state["_saas_auth_bootstrap_attempts"] = 6
        with (patch.object(saas_core, "_restore_session_from_cookie", return_value=False),
              patch.object(saas_core.time, "time", return_value=103.0)):
            self.assertFalse(saas_core._auth_bootstrap_gate())
        self.assertTrue(saas_core.st.session_state.get("_saas_auth_bootstrap_done"))
        self.assertNotIn("saas_auth_error", saas_core.st.session_state)

    def test_auth_bootstrap_terminal_cookie_failure_does_not_leak_stale_error_to_login(self):
        saas_core.st.session_state["saas_auth_error"] = "stale backend detail"
        saas_core.st.session_state["_saas_cookie_restore_failed"] = True
        with patch.object(saas_core, "_restore_session_from_cookie", return_value=False):
            self.assertFalse(saas_core._auth_bootstrap_gate())
        self.assertNotIn("saas_auth_error", saas_core.st.session_state)

    def test_auth_bootstrap_marks_terminal_cookie_failure_without_auth_error(self):
        saas_core.st.session_state["_saas_cookie_restore_failed"] = True
        with patch.object(saas_core, "_restore_session_from_cookie", return_value=False):
            self.assertFalse(saas_core._auth_bootstrap_gate())
        self.assertTrue(saas_core.st.session_state.get("_saas_auth_bootstrap_done"))
        self.assertNotIn("saas_auth_error", saas_core.st.session_state)


if __name__ == "__main__":
    unittest.main()
