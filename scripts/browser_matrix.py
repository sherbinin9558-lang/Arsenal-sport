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
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error"
                    else None,
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
                    if console_errors:
                        raise RuntimeError(
                            "browser console errors: " + " | ".join(console_errors[:5])
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
                        "console_errors": console_errors[:20],
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
