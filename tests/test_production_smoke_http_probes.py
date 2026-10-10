import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import playwright_production_smoke as smoke


class ProductionSmokeHttpProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_out = smoke.OUT
        smoke.OUT = Path(self.temp_dir.name)
        self.addCleanup(setattr, smoke, "OUT", self.original_out)

    @staticmethod
    def auth_redirect():
        return SimpleNamespace(
            status_code=303,
            text="See Other",
            headers={
                "Location": "https://share.streamlit.io/-/auth/app?redirect_uri=https%3A%2F%2Fexample.streamlit.app"
            },
        )

    def test_health_probe_continues_on_streamlit_auth_redirect(self):
        with patch.object(smoke.requests, "get", return_value=self.auth_redirect()):
            smoke.health_check()

        report = json.loads((smoke.OUT / "health.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], 303)
        self.assertIn("share.streamlit.io/-/auth/", report["location"])

    def test_homepage_probe_continues_on_streamlit_auth_redirect(self):
        with patch.object(smoke.requests, "get", return_value=self.auth_redirect()):
            smoke.startup_http_probe()

        report = json.loads((smoke.OUT / "startup-http.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], 303)
        self.assertIn("share.streamlit.io/-/auth/", report["location"])

    def test_health_probe_still_fails_on_server_error(self):
        response = SimpleNamespace(status_code=503, text="unavailable", headers={})
        with patch.object(smoke.requests, "get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                smoke.health_check()


if __name__ == "__main__":
    unittest.main()
