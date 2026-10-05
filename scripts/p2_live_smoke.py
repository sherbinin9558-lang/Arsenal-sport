#!/usr/bin/env python3
"""Optional live P2 verification harness.

No payment is charged and no social post is published by default.
Set explicit environment variables to enable provider/browser checks.
"""
import os
import sys
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


NO_REDIRECT_OPENER = build_opener(NoRedirectHandler())


def http(url, timeout=15, follow_redirects=True):
    start = time.perf_counter()
    opener = build_opener() if follow_redirects else NO_REDIRECT_OPENER
    try:
        req = Request(url, headers={"User-Agent": "ArsenalSport-P2-Smoke/1.0"})
        with opener.open(req, timeout=timeout) as r:
            body = r.read(4096)
            return True, r.status, time.perf_counter() - start, body
    except (HTTPError, URLError, TimeoutError) as e:
        return False, getattr(e, "code", 0), time.perf_counter() - start, str(e).encode()


def load_test(url, workers=20, requests_count=100):
    """Exercise the Streamlit health endpoint concurrently.

    The public Streamlit app root is session/UI traffic and is not a stable
    load-test target: concurrent root requests can be slow while the app
    wakes or creates sessions. The authenticated browser smoke separately
    verifies the real UI. Streamlit documents /_stcore/health as its health
    endpoint/readiness probe.
    """
    target = url.rstrip("/") + "/_stcore/health"
    lat = []
    failures = 0
    statuses = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(http, target, 20, False) for _ in range(requests_count)]
        for f in as_completed(futures):
            ok, status, elapsed, body = f.result()
            lat.append(elapsed)
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            if status not in (200, 303):
                failures += 1
                key = f"{status}:{body.decode('utf-8', 'replace')[:120]}"
                errors[key] = errors.get(key, 0) + 1

    result = {
        "target": target,
        "requests": requests_count,
        "workers": workers,
        "failures": int(failures),
        "statuses": statuses,
        "p50_ms": round(statistics.median(lat) * 1000, 1),
        "p95_ms": round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)] * 1000, 1),
        "max_ms": round(max(lat) * 1000, 1),
    }
    if errors:
        result["errors"] = errors
    return result


def telegram_readonly():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "TELEGRAM_BOT_TOKEN not set"}
    ok, status, elapsed, body = http(f"https://api.telegram.org/bot{token}/getMe")
    return {
        "status": "ok" if ok else "failed",
        "http": status,
        "latency_ms": round(elapsed * 1000, 1),
        "body": body.decode("utf-8", "replace")[:500],
    }


def vk_readonly():
    token = os.getenv("VK_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "VK_TOKEN not set"}
    import urllib.parse

    req = Request(
        "https://api.vk.com/method/users.get",
        data=urllib.parse.urlencode({"access_token": token, "v": "5.199"}).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ArsenalSport-P2-Smoke/1.0",
        },
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=15) as r:
            body = r.read(4096)
            ok, status = True, r.status
    except (HTTPError, URLError, TimeoutError) as e:
        body = str(e).encode()
        ok, status = False, getattr(e, "code", 0)
    elapsed = time.perf_counter() - start
    return {
        "status": "ok" if ok else "failed",
        "http": status,
        "latency_ms": round(elapsed * 1000, 1),
        "body": body.decode("utf-8", "replace")[:500],
    }


def browser_webmcp():
    url = os.getenv("SAAS_PUBLIC_URL", "").strip()
    if not url:
        return {"status": "skipped", "reason": "SAAS_PUBLIC_URL not set"}
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"status": "skipped", "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)

            email = os.getenv("E2E_EMAIL", "").strip()
            password = os.getenv("E2E_PASSWORD", "")
            if not email or not password:
                return {"status": "skipped", "reason": "E2E credentials not set"}

            # Streamlit renders controls from inactive tabs too. Activate the
            # login tab and target only visible controls in the active DOM.
            login_tab = page.get_by_role("tab", name="Войти", exact=True)
            if login_tab.count() > 0:
                login_tab.first.click()

            # Streamlit can render text inputs with different HTML input types
            # across versions. Use semantic labels and visibility instead of
            # assuming the email field is input[type=text].
            email_field = page.get_by_label("Email", exact=True)
            password_field = page.get_by_label("Пароль", exact=True)
            login_buttons = page.locator("button:visible").filter(has_text="Войти")

            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if (
                    email_field.count() > 0
                    and password_field.count() > 0
                    and email_field.first.is_visible()
                    and password_field.first.is_visible()
                    and login_buttons.count() > 0
                ):
                    break
                page.wait_for_timeout(1000)

            diagnostics = {
                "email_label_count": email_field.count(),
                "password_label_count": password_field.count(),
                "visible_inputs": page.locator("input:visible").count(),
                "visible_login_buttons": login_buttons.count(),
            }
            if (
                email_field.count() < 1
                or password_field.count() < 1
                or not email_field.first.is_visible()
                or not password_field.first.is_visible()
                or login_buttons.count() < 1
            ):
                page.screenshot(path="artifacts/smoke/login-form-missing.png", full_page=True)
                raise RuntimeError(
                    "Authenticated login form was not found: "
                    + json.dumps(diagnostics, ensure_ascii=False)
                )

            email_field.first.fill(email)
            password_field.first.fill(password)
            login_buttons.last.click()

            page.wait_for_timeout(5000)
            os.makedirs("artifacts/smoke", exist_ok=True)
            page.screenshot(path="artifacts/smoke/authenticated-home.png", full_page=True)

            # A successful login must remove the visible password field. This
            # avoids confusing the inactive login tab's hidden DOM controls
            # with the authenticated application state.
            if page.locator('input[type="password"]:visible').count() > 0:
                raise RuntimeError("Authenticated login did not complete.")

            result = page.evaluate("""() => ({
              url: location.href,
              hasWebMcpSdk: !!globalThis.__WEBMCP_TELEMETRY__,
              registered: !!globalThis.__ARSENAL_WEBMCP_READY__
            })""")
        finally:
            browser.close()

    if not result.get("registered"):
        raise RuntimeError("WebMCP registration marker was not detected.")
    return {"status": "ok", "result": result}


def main():
    report = {}
    app_url = os.getenv("SAAS_PUBLIC_URL", "").strip()
    if app_url:
        report["load_test"] = load_test(
            app_url,
            int(os.getenv("LOAD_WORKERS", "20")),
            int(os.getenv("LOAD_REQUESTS", "100")),
        )
    else:
        report["load_test"] = {"status": "skipped", "reason": "SAAS_PUBLIC_URL not set"}

    report["telegram"] = telegram_readonly()
    report["vk"] = vk_readonly()

    try:
        report["webmcp"] = browser_webmcp()
    except Exception as exc:
        report["webmcp"] = {"status": "failed", "error": str(exc)}

    with open("smoke-report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return (
        0
        if all(x.get("status") != "failed" for x in [report["telegram"], report["vk"], report["webmcp"]])
        and report["load_test"].get("failures", 0) == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
