"""Public, unauthenticated browser smoke tests for the isolated test deployment.

These checks intentionally do not log in or mutate application data. Authenticated
login/logout and tenant-isolation flows require dedicated test credentials and are
not claimed by this suite.
"""
import os

import pytest
from playwright.sync_api import sync_playwright


def _base_url():
    value = os.getenv("E2E_BASE_URL", "").strip()
    if not value:
        pytest.skip("E2E_BASE_URL is not configured.")
    return value.rstrip("/")


@pytest.mark.e2e
def test_public_app_loads_without_uncaught_browser_errors_or_streamlit_exception():
    base_url = _base_url()
    browser_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        response = page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        assert response is not None, "The app returned no navigation response."
        assert response.status < 500, f"App returned HTTP {response.status}"
        page.locator("body").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1500)
        body = page.locator("body").inner_text().lower()
        assert body.strip(), "The public page rendered an empty body."
        assert page.locator("[data-testid='stException']").count() == 0, (
            "Streamlit rendered an exception panel on the public page."
        )
        browser.close()
    assert not browser_errors, "Uncaught browser errors: " + "; ".join(browser_errors)


@pytest.mark.e2e
def test_public_auth_screen_exposes_an_email_or_password_input():
    base_url = _base_url()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        response = page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        assert response is not None and response.status < 500
        page.locator("body").wait_for(state="visible", timeout=10000)
        auth_words = ("войти", "login", "sign in", "авториза", "вход")
        # Streamlit Community Cloud can return its shell before the Python app
        # finishes starting. Wait for actual login content instead of sampling
        # the body only 1.5 seconds after navigation.
        page.wait_for_function(
            """words => {
                const text = (document.body?.innerText || '').toLowerCase();
                return words.some(word => text.includes(word));
            }""",
            arg=list(auth_words),
            timeout=45000,
        )
        body = page.locator("body").inner_text().lower()
        fields = page.locator("input")
        field_text = []
        for i in range(fields.count()):
            field = fields.nth(i)
            field_text.extend([
                (field.get_attribute("type") or "").lower(),
                (field.get_attribute("placeholder") or "").lower(),
                (field.get_attribute("aria-label") or "").lower(),
            ])
        combined = " ".join(field_text)
        assert any(word in combined for word in (
            "password", "email", "парол", "почт"
        )) or "text" in field_text, (
            "Login screen is present but no email/password-like input was found."
        )
        browser.close()
