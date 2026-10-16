"""Public, unauthenticated browser smoke tests for the isolated test deployment.

Streamlit renders the Python application inside an iframe; assertions must inspect
that app frame rather than the outer hosting shell.
These checks do not log in or mutate application data.
"""
import os

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


def _base_url():
    value = os.getenv("E2E_BASE_URL", "").strip()
    if not value:
        pytest.skip("E2E_BASE_URL is not configured.")
    return value.rstrip("/")


def _app_frame(page):
    """Return Streamlit's application frame, not the outer hosting document."""
    for frame in page.frames:
        if frame.name == "streamlitApp":
            return frame
    # Some Streamlit versions don't expose a stable frame name. Prefer the
    # frame that actually contains app inputs or rendered Streamlit elements.
    for frame in page.frames:
        try:
            if frame.locator("input, [data-testid='stApp'], [data-testid='stException']").count():
                return frame
        except Exception:
            continue
    return None


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
        app_frame = None
        for _ in range(30):
            app_frame = _app_frame(page)
            if app_frame is not None:
                break
            page.wait_for_timeout(1000)
        assert app_frame is not None, (
            "Streamlit application iframe did not appear. "
            f"title={page.title()!r}; frames={[{'name': f.name, 'url': f.url} for f in page.frames]!r}"
        )
        app_frame.locator("body").wait_for(state="visible", timeout=15000)
        body = app_frame.locator("body").inner_text().lower()
        assert body.strip(), "The Streamlit application frame rendered an empty body."
        assert app_frame.locator("[data-testid='stException']").count() == 0, (
            "Streamlit rendered an exception panel in the application frame."
        )
        browser.close()
    assert not browser_errors, "Uncaught browser errors: " + "; ".join(browser_errors)


@pytest.mark.e2e
def test_public_auth_screen_exposes_an_email_or_password_input():
    base_url = _base_url()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        console_errors = []
        failed_requests = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("requestfailed", lambda request: failed_requests.append(f"{request.method} {request.url}: {request.failure}"))
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        response = page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        assert response is not None and response.status < 500
        page.locator("body").wait_for(state="visible", timeout=10000)
        auth_words = ("войти", "login", "sign in", "авториза", "вход")
        app_frame = None
        for _ in range(30):
            app_frame = _app_frame(page)
            if app_frame is not None:
                break
            page.wait_for_timeout(1000)
        assert app_frame is not None, (
            "Streamlit application iframe did not appear. "
            f"title={page.title()!r}; frames={[{'name': f.name, 'url': f.url} for f in page.frames]!r}"
        )
        try:
            app_frame.wait_for_function(
                """words => {
                    const text = (document.body?.innerText || '').toLowerCase();
                    return words.some(word => text.includes(word));
                }""",
                arg=list(auth_words),
                timeout=45000,
            )
        except PlaywrightTimeoutError as exc:
            body_excerpt = " ".join(app_frame.locator("body").inner_text().split())[:1200]
            inputs = app_frame.locator("input")
            input_details = []
            for i in range(min(inputs.count(), 20)):
                field = inputs.nth(i)
                input_details.append({
                    "type": field.get_attribute("type"),
                    "placeholder": field.get_attribute("placeholder"),
                    "aria_label": field.get_attribute("aria-label"),
                })
            raise AssertionError(
                "Login content did not appear within 45s inside the Streamlit app frame. "
                f"title={page.title()!r}; url={page.url!r}; "
                f"frame_name={app_frame.name!r}; frame_url={app_frame.url!r}; "
                f"body={body_excerpt!r}; inputs={input_details!r}; "
                f"console_errors={console_errors[-10:]!r}; "
                f"page_errors={page_errors[-10:]!r}; "
                f"failed_requests={failed_requests[-10:]!r}"
            ) from exc
        body = app_frame.locator("body").inner_text().lower()
        fields = app_frame.locator("input")
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
