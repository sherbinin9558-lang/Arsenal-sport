import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv(
    "SAAS_PUBLIC_URL",
    "https://arsenal-sport-b3rvpnysmxhvw9wud8wjjd.streamlit.app",
).rstrip("/")
OUT = Path("artifacts/browserstack-production")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    username = os.environ["BROWSERSTACK_USERNAME"]
    access_key = os.environ["BROWSERSTACK_ACCESS_KEY"]
    ws_endpoint = "wss://cdp.browserstack.com/playwright?caps="

    capabilities = {
        "browser": "Chrome",
        "browser_version": "latest",
        "os": "android",
        "os_version": "14.0",
        "device": "Samsung Galaxy S24",
        "name": "Arsenal Sport production smoke",
        "build": "Arsenal Sport production",
        "browserstack.username": username,
        "browserstack.accessKey": access_key,
        "browserstack.networkLogs": "true",
        "browserstack.console": "verbose",
    }

    import urllib.parse

    with sync_playwright() as pw:
        browser = pw.chromium.connect(
            ws_endpoint + urllib.parse.quote(json.dumps(capabilities))
        )
        page = browser.new_page()
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=90000)
            page.get_by_text("Ваш магазин. Один рабочий центр.").first.wait_for(
                state="visible", timeout=90000
            )
            page.get_by_label("Email").wait_for(state="visible", timeout=30000)
            page.get_by_label("Пароль").wait_for(state="visible", timeout=30000)
            result = {"status": "PASS", "url": page.url}
        except Exception as exc:
            result = {
                "status": "FAIL",
                "url": page.url,
                "error": str(exc),
                "body": page.locator("body").inner_text(timeout=10000)[:12000],
            }
            page.screenshot(path=str(OUT / "failure.png"), full_page=True)
            raise
        finally:
            (OUT / "report.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            browser.close()


if __name__ == "__main__":
    main()
