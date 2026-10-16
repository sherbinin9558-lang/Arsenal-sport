"""Public, unauthenticated browser smoke tests for the isolated test deployment."""
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


def _base_url():
    value = os.getenv("E2E_BASE_URL", "").strip()
    if not value:
        pytest.skip("E2E_BASE_URL is not configured.")
    return value.rstrip("/")


def _is_streamlit_app_frame(frame):
    """Only accept the deployed Streamlit app; status/analytics embeds are not the app."""
    host = (urlparse(frame.url).hostname or "").lower()
    return host.endswith(".streamlit.app") or host.endswith(".streamlit.io")


def _visible_app_frame(page, timeout_ms=45000):
    """Find the actual Streamlit app document, ignoring Statuspage and cookie-controller frames."""
    deadline = timeout_ms
    while deadline > 0:
        for frame in page.frames:
            if frame == page.main_frame or not _is_streamlit_app_frame(frame):
                continue
            try:
                body = frame.locator("body")
                text = body.inner_text(timeout=500).strip()
                if text and any(marker in text.lower() for marker in ("ai agent content manager", "единый рабочий центр", "войти", "каталог")):
                    return frame
            except Exception:
                pass
        page.wait_for_timeout(500)
        deadline -= 500
    frame_info = []
    for frame in page.frames:
        try:
            frame_info.append({
                "name": frame.name,
                "url": frame.url,
                "is_streamlit_app": _is_streamlit_app_frame(frame),
                "body_visible": frame.locator("body").is_visible(),
                "body_text": " ".join(frame.locator("body").inner_text(timeout=500).split())[:180],
            })
        except Exception as exc:
            frame_info.append({"name": frame.name, "url": frame.url, "error": str(exc)[:120]})
    raise AssertionError(
        "No Streamlit app document with expected application content appeared. "
        f"title={page.title()!r}; frames={frame_info!r}"
    )


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
        app_frame = _visible_app_frame(page)
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
        app_frame = _visible_app_frame(page)
        auth_words = ("войти", "login", "sign in", "авториза", "вход")
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
                "Login content did not appear within 45s inside the visible Streamlit app frame. "
                f"title={page.title()!r}; url={page.url!r}; "
                f"frame_name={app_frame.name!r}; frame_url={app_frame.url!r}; "
                f"body={body_excerpt!r}; inputs={input_details!r}; "
                f"console_errors={console_errors[-10:]!r}; "
                f"page_errors={page_errors[-10:]!r}; "
                f"failed_requests={failed_requests[-10:]!r}"
            ) from exc
        # Streamlit widgets can be hosted in nested frames depending on the deployed shell.
        # Search every frame, not only the frame that contains the visible login heading.
        input_details = []
        for candidate_frame in page.frames:
            try:
                fields = candidate_frame.locator("input")
                for i in range(min(fields.count(), 30)):
                    field = fields.nth(i)
                    input_details.append({
                        "frame_url": candidate_frame.url,
                        "type": (field.get_attribute("type") or "").lower(),
                        "placeholder": (field.get_attribute("placeholder") or "").lower(),
                        "aria_label": (field.get_attribute("aria-label") or "").lower(),
                        "visible": field.is_visible(),
                    })
            except Exception:
                continue
        relevant_inputs = [
            field for field in input_details
            if any(word in " ".join((field["type"], field["placeholder"], field["aria_label"]))
                   for word in ("password", "email", "парол", "почт"))
            or field["type"] == "text"
        ]
        visible_auth_input = any(field["visible"] for field in relevant_inputs)
        if not visible_auth_input:
            # Preserve evidence when the login heading renders without usable fields.
            artifact_dir = Path("artifacts")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(artifact_dir / "public-auth-screen.png"), full_page=True)
            dom_inventory = []
            for candidate_frame in page.frames:
                try:
                    dom_inventory.append({
                        "url": candidate_frame.url,
                        "title": candidate_frame.title(),
                        "body_text": " ".join(candidate_frame.locator("body").inner_text(timeout=1000).split())[:1200],
                        "input_count": candidate_frame.locator("input").count(),
                        "button_count": candidate_frame.locator("button").count(),
                        "tab_count": candidate_frame.locator("[role='tab']").count(),
                    })
                except Exception as exc:
                    dom_inventory.append({"url": candidate_frame.url, "error": str(exc)[:160]})
        assert visible_auth_input, (
            "Login text was detected, but no visible email/password/text input was found "
            f"in any browser frame. frames={[{'name': f.name, 'url': f.url} for f in page.frames]!r}; "
            f"inputs={input_details!r}; dom_inventory={dom_inventory if not visible_auth_input else []!r}; "
            f"console_errors={console_errors[-10:]!r}; page_errors={page_errors[-10:]!r}; "
            f"failed_requests={failed_requests[-10:]!r}"
        )
        browser.close()
