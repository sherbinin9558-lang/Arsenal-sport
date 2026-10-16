"""Public, unauthenticated browser smoke tests for the isolated test deployment."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


def _base_url():
    value = os.getenv("E2E_BASE_URL", "").strip()
    if not value:
        pytest.skip("E2E_BASE_URL is not configured.")
    return value.rstrip("/")



def _safe_url(value):
    """Remove query strings and fragments before writing URLs to diagnostics."""
    try:
        parsed = urlparse(value)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return "<invalid-url>"


def _source_for_url(value, app_host):
    host = (urlparse(value).hostname or "").lower()
    if host == app_host:
        return "application"
    if host.endswith(".streamlit.app") or host.endswith(".streamlit.io"):
        return "streamlit"
    return "third_party"


def _network_event(response, app_host):
    request = response.request
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": response.status,
        "url": _safe_url(response.url),
        "resource_type": request.resource_type,
        "source": _source_for_url(response.url, app_host),
        "event_type": "http_response",
    }

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
                "url": _safe_url(frame.url),
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


def _write_public_diagnostics(page, label, details):
    """Persist sanitized public-page evidence for both passing and failing runs."""
    artifact_dir = Path("artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_details = {
        "label": label,
        "page_url": _safe_url(page.url),
        "page_title": page.title(),
        "frames": [],
        **details,
    }
    for frame in page.frames:
        item = {"name": frame.name, "url": _safe_url(frame.url)}
        try:
            body_text = " ".join(frame.locator("body").inner_text(timeout=1000).split())
            item.update({
                "body_text_excerpt": body_text[:800],
                "input_count": frame.locator("input").count(),
                "visible_input_count": sum(
                    1 for i in range(min(frame.locator("input").count(), 30))
                    if frame.locator("input").nth(i).is_visible()
                ),
                "button_count": frame.locator("button").count(),
            })
        except Exception as exc:
            item["inspection_error"] = str(exc)[:160]
        safe_details["frames"].append(item)
    (artifact_dir / f"{label}.json").write_text(
        json.dumps(safe_details, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # The public unauthenticated screen contains no entered credentials.
    page.screenshot(path=str(artifact_dir / f"{label}.png"), full_page=True)


@pytest.mark.e2e
def test_public_app_loads_without_uncaught_browser_errors_or_streamlit_exception():
    base_url = _base_url()
    browser_errors = []
    console_errors = []
    failed_app_requests = []
    server_errors = []
    http_diagnostics = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        app_host = (urlparse(base_url).hostname or "").lower()

        def is_app_url(url):
            host = (urlparse(url).hostname or "").lower()
            return host == app_host or host.endswith(".streamlit.app") or host.endswith(".streamlit.io")

        page.on("pageerror", lambda error: browser_errors.append(str(error)[:300]))
        page.on("console", lambda msg: console_errors.append(msg.type + ": " + msg.text[:300]) if msg.type == "error" else None)

        def on_request_failed(request):
            if is_app_url(request.url):
                failed_app_requests.append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "method": request.method,
                    "url": _safe_url(request.url),
                    "resource_type": request.resource_type,
                    "source": _source_for_url(request.url, app_host),
                    "event_type": "request_failed",
                    "failure": str(request.failure or "unknown")[:120],
                })

        def on_response(response):
            if response.status in (403, 404) or (response.status >= 500 and is_app_url(response.url)):
                http_diagnostics.append(_network_event(response, app_host))
                if response.status >= 500 and is_app_url(response.url):
                    server_errors.append(f"HTTP {response.status} {_safe_url(response.url)}")

        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)
        try:
            response = page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            assert response is not None, "The app returned no navigation response."
            assert response.status < 500, f"App returned HTTP {response.status}"
            app_frame = _visible_app_frame(page)
            _write_public_diagnostics(page, "public-app-smoke", {
                "browser_errors": browser_errors[-10:],
                "console_errors": console_errors[-10:],
                "failed_app_requests": failed_app_requests[-10:],
                "server_errors": server_errors[-10:],
                "http_diagnostics": http_diagnostics[-100:],
                "streamlit_exception_count": app_frame.locator("[data-testid='stException']").count(),
            })
            assert app_frame.locator("[data-testid='stException']").count() == 0, (
                "Streamlit rendered an exception panel in the application frame."
            )
            assert not browser_errors, "Uncaught JavaScript errors: " + "; ".join(browser_errors[-10:])
            assert not server_errors, "App-origin server errors: " + "; ".join(server_errors[-10:])
            assert not failed_app_requests, "Failed app-origin requests: " + "; ".join(failed_app_requests[-10:])
        finally:
            context.close()
            browser.close()
    assert not browser_errors, "Uncaught JavaScript errors: " + "; ".join(browser_errors[-10:])
    assert not server_errors, "App-origin server errors: " + "; ".join(server_errors[-10:])
    assert not failed_app_requests, "Failed app-origin requests: " + "; ".join(failed_app_requests[-10:])
    # Console errors are recorded for diagnostics; third-party embeds can emit harmless errors.
    # The Streamlit exception panel and uncaught JavaScript exceptions remain hard failures.


@pytest.mark.e2e
def test_public_auth_screen_exposes_an_email_or_password_input():
    base_url = _base_url()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        console_errors = []
        failed_requests = []
        page_errors = []
        http_diagnostics = []
        app_host = (urlparse(base_url).hostname or "").lower()
        page.on("console", lambda msg: console_errors.append(msg.type + ": " + msg.text[:300]) if msg.type == "error" else None)
        page.on("requestfailed", lambda request: failed_requests.append({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "url": _safe_url(request.url),
            "resource_type": request.resource_type,
            "source": _source_for_url(request.url, app_host),
            "event_type": "request_failed",
            "failure": str(request.failure or "unknown")[:120],
        }))
        page.on("response", lambda response: http_diagnostics.append(_network_event(response, app_host))
                  if response.status in (403, 404) or response.status >= 500 else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)[:300]))
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
                        "frame_url": _safe_url(candidate_frame.url),
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
                        "url": _safe_url(candidate_frame.url),
                        "title": candidate_frame.title(),
                        "body_text": " ".join(candidate_frame.locator("body").inner_text(timeout=1000).split())[:1200],
                        "input_count": candidate_frame.locator("input").count(),
                        "button_count": candidate_frame.locator("button").count(),
                        "tab_count": candidate_frame.locator("[role='tab']").count(),
                    })
                except Exception as exc:
                    dom_inventory.append({"url": candidate_frame.url, "error": str(exc)[:160]})
        _write_public_diagnostics(page, "public-auth-screen", {
            "visible_auth_input": visible_auth_input,
            "auth_words_detected": True,
            "input_inventory": input_details,
            "console_errors": console_errors[-10:],
            "page_errors": page_errors[-10:],
            "failed_requests": failed_requests[-30:],
            "http_diagnostics": http_diagnostics[-100:],
        })
        assert visible_auth_input, (
            "Login text was detected, but no visible email/password/text input was found "
            f"in any browser frame. frames={[{'name': f.name, 'url': f.url} for f in page.frames]!r}; "
            f"inputs={input_details!r}; dom_inventory={dom_inventory if not visible_auth_input else []!r}; "
            f"console_errors={console_errors[-10:]!r}; page_errors={page_errors[-10:]!r}; "
            f"failed_requests={failed_requests[-10:]!r}"
        )
        browser.close()
