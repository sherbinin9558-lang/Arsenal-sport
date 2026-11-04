"""Regression tests for refresh-token rotation on hard browser reloads."""

import unittest
from unittest.mock import patch

import saas_core


class RerunRequested(Exception):
    """Test sentinel for Streamlit's rerun control flow."""


class FakeCookieController:
    def __init__(self, values, refresh_error=None):
        self.values = values
        self.refresh_error = refresh_error

    def refresh(self):
        if self.refresh_error:
            raise self.refresh_error
        return None

    def getAll(self):
        return dict(self.values)

    def get(self, name):
        return self.values.get(name)


class FakeStreamlit:
    def __init__(self, session_state):
        self.session_state = session_state

    def rerun(self):
        raise RerunRequested()


class RefreshCookiePriorityTests(unittest.TestCase):
    def test_prefers_live_cookie_controller_over_stale_request_snapshot(self):
        # The live browser component contains the rotated token; request cookies
        # are intentionally not consulted when CookieController is available.
        state = {}
        controller = FakeCookieController({"saas_refresh_token": "current-rotated-token"})
        with patch.object(saas_core, "st", FakeStreamlit(state)), patch.object(
            saas_core, "_auth_cookies", return_value=controller
        ):
            token = saas_core._read_refresh_token()

        self.assertEqual(token, "current-rotated-token")

    def test_refresh_failure_does_not_return_cached_stale_token(self):
        state = {"_saas_cookie_probe_count": 0}
        controller = FakeCookieController(
            {"saas_refresh_token": "stale-token"},
            refresh_error=RuntimeError("component not hydrated"),
        )
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_auth_cookies", return_value=controller
        ):
            token = saas_core._read_refresh_token()

        self.assertIsNone(token)

    def test_empty_first_probe_requests_one_rerun_for_cookie_hydration(self):
        state = {"_saas_cookie_probe_count": 1}
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_restore_session_from_cookie", return_value=False
        ), patch.object(saas_core, "CookieController", new=FakeCookieController):
            with self.assertRaises(RerunRequested):
                saas_core._auth_bootstrap_gate()

    def test_second_empty_probe_falls_back_to_login_without_another_rerun(self):
        state = {"_saas_cookie_probe_count": 2}
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_restore_session_from_cookie", return_value=False
        ), patch.object(saas_core, "CookieController", new=FakeCookieController):
            result = saas_core._auth_bootstrap_gate()

        self.assertFalse(result)

    def test_delayed_cookie_hydration_restores_on_second_gate_execution(self):
        # Simulate the browser component being empty on the first Streamlit run,
        # then receiving the valid cookie before the single permitted rerun.
        state = {}
        controller = FakeCookieController({})
        fake_st = FakeStreamlit(state)

        def restore_from_cookie():
            token = saas_core._read_refresh_token()
            if not token:
                return False
            # Model the successful downstream session restoration only after the
            # actual cookie reader returns the hydrated browser token.
            state["saas_access_token"] = "restored-access-token"
            return True

        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_auth_cookies", return_value=controller
        ), patch.object(
            saas_core, "_restore_session_from_cookie", side_effect=restore_from_cookie
        ):
            with self.assertRaises(RerunRequested):
                saas_core._auth_bootstrap_gate()

            self.assertEqual(state.get("_saas_cookie_probe_count"), 1)
            self.assertNotIn("saas_access_token", state)

            controller.values["saas_refresh_token"] = "hydrated-valid-token"
            result = saas_core._auth_bootstrap_gate()

        self.assertTrue(result)
        self.assertEqual(state.get("saas_access_token"), "restored-access-token")
        self.assertEqual(state.get("_saas_cookie_probe_count"), 2)

    def test_confirmed_invalid_token_does_not_request_hydration_retry(self):
        state = {"_saas_cookie_probe_count": 1, "_saas_cookie_restore_failed": True}
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_restore_session_from_cookie"
        ) as restore, patch.object(saas_core, "CookieController", new=FakeCookieController):
            result = saas_core._auth_bootstrap_gate()

        self.assertFalse(result)
        restore.assert_not_called()

    def test_explicit_logout_does_not_request_hydration_retry(self):
        state = {"_saas_cookie_probe_count": 1, "_saas_logout_completed": True}
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_restore_session_from_cookie"
        ) as restore, patch.object(saas_core, "CookieController", new=FakeCookieController):
            result = saas_core._auth_bootstrap_gate()

        self.assertFalse(result)
        restore.assert_not_called()


if __name__ == "__main__":
    unittest.main()
