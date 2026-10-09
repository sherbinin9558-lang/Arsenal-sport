"""Optional E2E checks against a separately configured test deployment.

Set E2E_BASE_URL in GitHub Actions variables. Do not target production unless
you have a dedicated test tenant and safe test credentials.
"""
import os
import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.e2e
def test_public_app_loads_without_uncaught_browser_errors():
    base_url = os.getenv("E2E_BASE_URL")
    if not base_url:
        pytest.skip("E2E_BASE_URL is not configured.")
    browser_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        response = page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        assert response is not None, "The app returned no navigation response."
        assert response.status < 500, f"App returned HTTP {response.status}"
        page.wait_for_timeout(1500)
        browser.close()
    assert not browser_errors, "Uncaught browser errors: " + "; ".join(browser_errors)


@pytest.mark.e2e
def test_login_related_page_has_password_or_email_field():
    base_url = os.getenv("E2E_BASE_URL")
    if not base_url:
        pytest.skip("E2E_BASE_URL is not configured.")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        body = page.locator("body").inner_text().lower()
        if any(word in body for word in ("войти", "login", "sign in", "авториза")):
            assert any(word in body for word in ("парол", "password", "email", "почт"))
        browser.close()
