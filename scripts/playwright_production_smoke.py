import json
import os
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


BASE_URL = os.getenv(
    "SAAS_PUBLIC_URL",
    "https://arsenal-sport-b3rvpnysmxhvw9wud8wjjd.streamlit.app",
).rstrip("/")
TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "90000"))
OUT = Path("artifacts/playwright-production")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ("desktop-chromium", "chromium", 1440, 1000),
    ("tablet-chromium", "chromium", 1024, 900),
    ("mobile-chromium", "chromium", 390, 844),
    ("desktop-firefox", "firefox", 1440, 1000),
    ("desktop-webkit", "webkit", 1440, 1000),
]


def health_check():
    url = f"{BASE_URL}/_stcore/health"
    started = time.perf_counter()
    response = requests.get(url, timeout=60)
    latency_ms = round((time.perf_counter() - started) * 1000)
    body = response.text.strip()
    result = {
        "url": url,
        "status": response.status_code,
        "body": body[:500],
        "latency_ms": latency_ms,
    }
    (OUT / "health.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if response.status_code != 200 or body != "ok":
        raise RuntimeError(f"Production health check failed: {result}")


def run():
    health_check()
    results = []
    with sync_playwright() as pw:
        for name, browser_name, width, height in TARGETS:
            browser = getattr(pw, browser_name).launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            console_errors = []
            page_errors = []
            request_failures = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on(
                "requestfailed",
                lambda req: request_failures.append(f"{req.method} {req.url}: {req.failure}"),
            )
            started = time.perf_counter()
            item = {"name": name, "browser": browser_name, "viewport": [width, height]}
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                page.get_by_text("Ваш магазин. Один рабочий центр.").first.wait_for(
                    state="visible", timeout=TIMEOUT_MS
                )
                page.get_by_label("Email").wait_for(state="visible", timeout=30000)
                page.get_by_label("Пароль").wait_for(state="visible", timeout=30000)
                item["status"] = "PASS"
            except Exception as exc:
                item["status"] = "FAIL"
                item["error"] = str(exc)
                item["url"] = page.url
                item["title"] = page.title()
                item["body"] = page.locator("body").inner_text(timeout=10000)[:12000]
                item["console_errors"] = console_errors[-100:]
                item["page_errors"] = page_errors[-100:]
                item["request_failures"] = request_failures[-100:]
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
            finally:
                item["duration_ms"] = round((time.perf_counter() - started) * 1000)
                results.append(item)
                browser.close()

    report = {"base_url": BASE_URL, "results": results}
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [x for x in results if x["status"] != "PASS"]
    if failures:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(f"{len(failures)} production browser checks failed")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
