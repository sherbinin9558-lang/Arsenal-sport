"""Regression tests for refresh-token rotation on hard browser reloads."""

import unittest
from unittest.mock import patch

import saas_core


class FakeCookieController:
    def __init__(self, values):
        self.values = values

    def refresh(self):
        return None

    def getAll(self):
        return dict(self.values)

    def get(self, name):
        return self.values.get(name)


class FakeStreamlit:
    def __init__(self, session_state):
        self.session_state = session_state


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

    def test_bootstrap_returns_login_state_instead_of_waiting_forever(self):
        state = {"_saas_cookie_probe_count": 1}
        fake_st = FakeStreamlit(state)
        with patch.object(saas_core, "st", fake_st), patch.object(
            saas_core, "_restore_session_from_cookie", return_value=False
        ), patch.object(saas_core, "CookieController", new=FakeCookieController):
            result = saas_core._auth_bootstrap_gate()

        self.assertFalse(result)

    def test_defers_when_cookie_component_has_not_hydrated(self):
        state = {}
        controller = FakeCookieController({})
        with patch.object(saas_core, "st", FakeStreamlit(state)), patch.object(
            saas_core, "_auth_cookies", return_value=controller
        ):
            token = saas_core._read_refresh_token()

        self.assertIsNone(token)
        self.assertEqual(state.get("_saas_cookie_probe_count"), 1)


if __name__ == "__main__":
    unittest.main()
