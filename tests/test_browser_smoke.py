import os
import subprocess
import sys
import time

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8501")


def _wait_for_app(url: str, timeout: float = 45.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic retry loop
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"Streamlit app did not become ready: {last_error}")


@pytest.fixture(scope="module")
def streamlit_app():
    if os.getenv("E2E_BASE_URL"):
        yield None
        return

    env = os.environ.copy()
    env.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless",
            "true",
            "--server.port",
            "8501",
            "--server.address",
            "127.0.0.1",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_app(BASE_URL)
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 1440, "height": 900, "name": "desktop"},
        {"width": 1024, "height": 768, "name": "tablet"},
        {"width": 390, "height": 844, "name": "mobile"},
    ],
)
def test_app_renders_without_server_error(streamlit_app, viewport):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport["width"], "height": viewport["height"]}
        )
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3000)

        body_text = page.locator("body").inner_text(timeout=10_000)
        assert "Exception" not in body_text, f"{viewport['name']} shows Exception"
        assert "Traceback" not in body_text, f"{viewport['name']} shows Traceback"
        assert "NameError" not in body_text, f"{viewport['name']} shows NameError"
        assert page.locator("body").count() == 1

        browser.close()
