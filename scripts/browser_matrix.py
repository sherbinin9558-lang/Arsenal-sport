#!/usr/bin/env python3
"""Read-only responsive browser smoke for the production Streamlit app."""
import json
import os
import sys
from pathlib import Path

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "tablet": {"width": 1024, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def find_visible_text(page, text, timeout_ms=60000):
    """Find text in the top-level document or any Streamlit app iframe."""
    import time
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for frame in list(page.frames):
            try:
                locator = frame.get_by_text(text, exact=False).first
                if locator.count() and locator.is_visible():
                    return locator, frame
            except Exception:
                continue
        page.wait_for_timeout(250)
    raise RuntimeError(f"Visible text {text!r} not found in page or attached frames within {timeout_ms} ms")


def find_visible_label(page, label, timeout_ms=30000):
    """Find a labelled control in the top-level document or an app iframe."""
    import time
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for frame in list(page.frames):
            try:
                locator = frame.get_by_label(label, exact=True).first
                if locator.count() and locator.is_visible():
                    return locator, frame
            except Exception:
                continue
        page.wait_for_timeout(250)
    raise RuntimeError(f"Visible label {label!r} not found in page or attached frames within {timeout_ms} ms")


def visible_text_all_frames(page):
    chunks = []
    for frame in page.frames:
        try:
            value = frame.locator("body").inner_text(timeout=3000).strip()
            if value:
                chunks.append(value)
        except Exception:
            continue
    return "\\n".join(chunks)


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
                    find_visible_text(page, "Ваш магазин. Один рабочий центр.", timeout_ms=60000)
                    email_field, app_frame = find_visible_label(page, "Email", timeout_ms=30000)
                    password_field, password_frame = find_visible_label(page, "Пароль", timeout_ms=30000)

                    mode = "public-login"
                    if authenticated:
                        email_field.fill(email)
                        password_field.fill(password)
                        login = app_frame.locator("button:visible").filter(has_text="Войти").last
                        login.wait_for(state="visible", timeout=10000)
                        login.click()
                        password_field.wait_for(state="hidden", timeout=45000)
                        page.wait_for_timeout(1000)
                        mode = "authenticated"

                    body_text = visible_text_all_frames(page)
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
