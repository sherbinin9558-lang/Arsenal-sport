#!/usr/bin/env python3
"""Read-only responsive browser smoke for the production Streamlit app."""
import json
import os
import sys
import time
from pathlib import Path

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "tablet": {"width": 1024, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def run():
    url = os.getenv("SAAS_PUBLIC_URL", "").strip()
    email = os.getenv("E2E_EMAIL", "").strip()
    password = os.getenv("E2E_PASSWORD", "")
    if not url:
        raise RuntimeError("SAAS_PUBLIC_URL is required")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("playwright is required for responsive browser smoke") from exc

    authenticated = bool(email and password)
    artifact_dir = Path("artifacts/browser-matrix")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-http2", "--disable-dev-shm-usage"],
        )
        try:
            for name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                console_errors = []
                auth_attempted = False
                failed_responses = []
                request_failures = []
                page.on(
                    "console",
                    lambda msg: console_errors.append({
                        "type": msg.type,
                        "text": msg.text,
                        "location": msg.location,
                    }) if msg.type == "error" else None,
                )
                page.on(
                    "response",
                    lambda response: failed_responses.append({
                        "url": response.url,
                        "status": response.status,
                        "method": response.request.method,
                        "resource_type": response.request.resource_type,
                    }) if response.status >= 400 else None,
                )
                page.on(
                    "requestfailed",
                    lambda request: request_failures.append({
                        "url": request.url,
                        "method": request.method,
                        "resource_type": request.resource_type,
                        "failure": request.failure,
                    }),
                )
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=90000)
                    # Community Cloud redirects private apps to its auth gateway.
                    # Detect that deployment condition immediately instead of waiting
                    # for a misleading UI-selector timeout.
                    if "share.streamlit.io/-/auth/" in page.url:
                        raise RuntimeError(
                            "PRODUCTION_ACCESS_BLOCKED: Streamlit Community Cloud requires "
                            "authentication for this app. Make the app public or provide "
                            "a dedicated E2E viewer session; application UI was not reached."
                        )
                    if response is not None and response.status >= 400:
                        raise RuntimeError(
                            f"PRODUCTION_HTTP_ERROR: initial document returned HTTP {response.status}"
                        )
                    # Streamlit Cloud may render the app in a late-attached iframe.
                    # Do not depend on marketing copy that can change independently of app readiness.
                    def visible_label(label, timeout_ms=60000):
                        deadline = time.monotonic() + timeout_ms / 1000
                        last_error = None
                        while time.monotonic() < deadline:
                            frames = [page.main_frame] + [
                                frame for frame in page.frames if frame != page.main_frame
                            ]
                            for frame in frames:
                                try:
                                    locator = frame.get_by_label(label, exact=True)
                                    if locator.count() and locator.first.is_visible():
                                        return locator.first
                                except Exception as exc:
                                    last_error = exc
                            page.wait_for_timeout(250)
                        raise RuntimeError(
                            f"Could not find visible {label!r} field in page or attached frames; "
                            f"last error: {last_error}"
                        )

                    email_field = visible_label("Email")
                    password_field = visible_label("Пароль")

                    mode = "public-login"
                    if authenticated:
                        auth_attempted = True
                        email_field.fill(email)
                        password_field.fill(password)
                        login = page.locator("button:visible").filter(has_text="Войти").last
                        login.wait_for(state="visible", timeout=10000)
                        login.click()
                        password_field.wait_for(state="hidden", timeout=45000)
                        page.wait_for_timeout(1000)
                        mode = "authenticated"

                    body_chunks = []
                    for frame in page.frames:
                        try:
                            chunk = frame.locator("body").inner_text(timeout=3000).strip()
                            if chunk:
                                body_chunks.append(chunk)
                        except Exception:
                            continue
                    body_text = "\\n".join(body_chunks)
                    horizontal_overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 2"
                    )
                    body_width = page.evaluate("() => document.body.scrollWidth")
                    viewport_width = page.evaluate("() => window.innerWidth")

                    if horizontal_overflow:
                        raise RuntimeError(
                            f"horizontal overflow: body={body_width}, viewport={viewport_width}"
                        )
                    if len(body_text.strip()) < 40:
                        raise RuntimeError("page rendered almost no text")
                    normalized_body = " ".join(body_text.split()).casefold()
                    if "ai agent content manager" not in normalized_body:
                        raise RuntimeError(
                            "APP_UI_NOT_CONFIRMED: login fields were found, but the expected "
                            "AI Agent Content Manager branding was not present in rendered app text"
                        )
                    if "создать магазин" not in normalized_body or "восстановить пароль" not in normalized_body:
                        raise RuntimeError(
                            "APP_LOGIN_UI_INCOMPLETE: expected login, create-shop, and password-recovery "
                            "navigation was not present in rendered app text"
                        )
                    # Ignore only known non-product noise. Keep all responses in the
                    # diagnostic report; the app-owned user-details 404 is ignored only
                    # before an authenticated login attempt.
                    def is_ignorable_console_error(item):
                        source_url = str((item.get("location") or {}).get("url", ""))
                        if source_url.startswith("https://sdk.us.heap-api.com/"):
                            return True
                        # Streamlit Community Cloud can reject its anonymous app-open
                        # telemetry POST while still serving the actual app UI. Keep the
                        # 403 in failed_responses for diagnosis, but do not fail a UI
                        # smoke solely on this non-product telemetry endpoint.
                        if (
                            not auth_attempted
                            and source_url.startswith(url.rstrip("/") + "/api/v1/app/event/open")
                        ):
                            return True
                        if (
                            not auth_attempted
                            and "/api/v2/user/details" in source_url
                            and source_url.startswith(url.rstrip("/") + "/")
                        ):
                            return True
                        return False

                    critical_console_errors = [
                        item for item in console_errors
                        if not is_ignorable_console_error(item)
                    ]
                    if critical_console_errors:
                        raise RuntimeError(
                            "browser console errors: " + " | ".join(
                                str(item.get("text", item))
                                for item in critical_console_errors[:5]
                            )
                        )

                    page.screenshot(path=str(artifact_dir / f"{name}.png"), full_page=True)
                    results[name] = {
                        "status": "ok",
                        "mode": mode,
                        "viewport": viewport,
                        "app_ready": True,
                        "horizontal_overflow": horizontal_overflow,
                        "text_length": len(body_text.strip()),
                    }
                except Exception as exc:
                    diagnostic = {
                        "status": "failed",
                        "viewport": viewport,
                        "url": page.url,
                        "title": page.title(),
                        "error": str(exc),
                        "console_errors": console_errors[-100:],
                        "failed_responses": failed_responses[-200:],
                        "request_failures": request_failures[-200:],
                        "frames": [],
                    }
                    for index, frame in enumerate(page.frames):
                        frame_info = {"index": index, "name": frame.name, "url": frame.url}
                        try:
                            frame_info["body_text"] = frame.locator("body").inner_text(timeout=5000)[:12000]
                        except Exception as frame_exc:
                            frame_info["body_text_error"] = str(frame_exc)
                        try:
                            html_path = artifact_dir / f"{name}-frame-{index}.html"
                            html_path.write_text(frame.content(), encoding="utf-8")
                            frame_info["html_file"] = html_path.name
                        except Exception as frame_exc:
                            frame_info["html_error"] = str(frame_exc)
                        diagnostic["frames"].append(frame_info)
                    def field_visible(label):
                        for frame in page.frames:
                            try:
                                locator = frame.get_by_label(label, exact=True)
                                if locator.count() and locator.first.is_visible():
                                    return True
                            except Exception:
                                continue
                        return False

                    diagnostic["app_readiness"] = {
                        "email_visible": field_visible("Email"),
                        "password_visible": field_visible("Пароль"),
                        "streamlit_statuspage_text_detected": any(
                            "status embed installed" in str(frame.get("body_text", "")).lower()
                            for frame in diagnostic["frames"]
                        ),
                    }
                    try:
                        diagnostic["body_text"] = page.locator("body").inner_text(timeout=5000)[:12000]
                    except Exception as body_exc:
                        diagnostic["body_text_error"] = str(body_exc)
                    try:
                        page.screenshot(path=str(artifact_dir / f"{name}-failure.png"), full_page=True)
                        diagnostic["screenshot"] = f"{name}-failure.png"
                    except Exception as screenshot_exc:
                        diagnostic["screenshot_error"] = str(screenshot_exc)
                    with open(artifact_dir / f"{name}-failure.json", "w", encoding="utf-8") as fh:
                        json.dump(diagnostic, fh, ensure_ascii=False, indent=2)
                    # A consolidated report survives the first failing viewport.
                    (artifact_dir / "failed_resources.json").write_text(
                        json.dumps({
                            "failed_responses": failed_responses[-200:],
                            "request_failures": request_failures[-200:],
                            "console_errors": console_errors[-100:],
                            "failed_viewport": name,
                            "diagnostic_file": f"{name}-failure.json",
                        }, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    raise
                finally:
                    page.close()
        finally:
            browser.close()

    with open("browser-matrix-report.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
