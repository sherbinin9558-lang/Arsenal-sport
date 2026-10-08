#!/usr/bin/env python3
"""Authenticated responsive browser smoke for the production Streamlit app.

This is read-only: it logs in, verifies the main app renders at desktop/tablet/mobile
viewports, checks the WebMCP registration marker, and records screenshots.
"""
import json
import os
import sys
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
    if not url or not email or not password:
        raise RuntimeError("SAAS_PUBLIC_URL, E2E_EMAIL and E2E_PASSWORD are required")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("playwright is required for responsive browser smoke") from exc

    Path("artifacts/browser-matrix").mkdir(parents=True, exist_ok=True)
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-http2", "--disable-dev-shm-usage"])
        try:
            for name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                console_errors = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_timeout(5000)

                    email_field = page.get_by_label("Email", exact=True)
                    password_field = page.get_by_label("Пароль", exact=True)
                    if email_field.count() == 0 or password_field.count() == 0:
                        raise RuntimeError("login fields not rendered")

                    email_field.first.fill(email)
                    password_field.first.fill(password)
                    login = page.locator("button:visible").filter(has_text="Войти")
                    if login.count() == 0:
                        raise RuntimeError("login button not rendered")
                    login.last.click()

                    deadline = page.locator('input[type="password"]:visible')
                    deadline.wait_for(state="hidden", timeout=30000)
                    page.wait_for_timeout(3000)

                    body = page.locator("body")
                    text = body.inner_text(timeout=10000)
                    app_ready = page.locator('[data-testid="stAppViewContainer"]').count() > 0
                    marker = page.evaluate("() => !!globalThis.__ARSENAL_WEBMCP_READY__")
                    horizontal_overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
                    body_width = page.evaluate("() => document.body.scrollWidth")
                    viewport_width = page.evaluate("() => window.innerWidth")

                    if not app_ready:
                        raise RuntimeError("Streamlit app container missing after login")
                    if not marker:
                        raise RuntimeError("WebMCP registration marker missing")
                    if horizontal_overflow:
                        raise RuntimeError(f"horizontal overflow: body={body_width}, viewport={viewport_width}")
                    if len(text.strip()) < 40:
                        raise RuntimeError("authenticated page rendered almost no text")
                    if console_errors:
                        raise RuntimeError("browser console errors: " + " | ".join(console_errors[:5]))

                    page.screenshot(path=f"artifacts/browser-matrix/{name}.png", full_page=True)
                    results[name] = {
                        "status": "ok",
                        "viewport": viewport,
                        "app_ready": app_ready,
                        "webmcp_registered": marker,
                        "horizontal_overflow": horizontal_overflow,
                        "text_length": len(text.strip()),
                    }
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
