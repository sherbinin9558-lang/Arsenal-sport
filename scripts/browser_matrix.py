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
    Path("artifacts/browser-matrix").mkdir(parents=True, exist_ok=True)
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
                    page.goto(url, wait_until="domcontentloaded", timeout=90000)

                    # Wait for the customer-facing shell before probing widgets.
                    # Streamlit widgets can appear asynchronously during reruns.
                    page.get_by_text("Ваш магазин. Один рабочий центр.", exact=False).first.wait_for(
                        state="visible", timeout=60000
                    )
                    email_field = page.get_by_label("Email", exact=True).first
                    password_field = page.get_by_label("Пароль", exact=True).first
                    email_field.wait_for(state="visible", timeout=30000)
                    password_field.wait_for(state="visible", timeout=30000)

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

                    text = page.locator("body").inner_text(timeout=10000)
                    horizontal_overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 2"
                    )
                    body_width = page.evaluate("() => document.body.scrollWidth")
                    viewport_width = page.evaluate("() => window.innerWidth")

                    if horizontal_overflow:
                        raise RuntimeError(
                            f"horizontal overflow: body={body_width}, viewport={viewport_width}"
                        )
                    if len(text.strip()) < 40:
                        raise RuntimeError("page rendered almost no text")
                    if console_errors:
                        raise RuntimeError(
                            "browser console errors: " + " | ".join(console_errors[:5])
                        )

                    page.screenshot(
                        path=f"artifacts/browser-matrix/{name}.png", full_page=True
                    )
                    results[name] = {
                        "status": "ok",
                        "mode": mode,
                        "viewport": viewport,
                        "app_ready": True,
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
