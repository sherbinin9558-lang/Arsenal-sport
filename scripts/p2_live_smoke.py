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


_NO_REDIRECT_OPENER = build_opener(NoRedirectHandler())


def http(url, timeout=15):
    start = time.perf_counter()
    try:
        req = Request(url, headers={"User-Agent": "ArsenalSport-P2-Smoke/1.0"})
        with _NO_REDIRECT_OPENER.open(req, timeout=timeout) as r:
            body = r.read(4096)
            return True, r.status, time.perf_counter() - start, body
    except HTTPError as e:
        return True, e.code, time.perf_counter() - start, str(e).encode()
    except (URLError, TimeoutError) as e:
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
        futures = [pool.submit(http, target, 20) for _ in range(requests_count)]
        for f in as_completed(futures):
            ok, status, elapsed, body = f.result()
            lat.append(elapsed)
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            if not ok or (status != 200 and status != 303) or (status == 200 and body.strip().lower() != b"ok"):
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
        return {"status": "failed", "reason": "TELEGRAM_BOT_TOKEN not set"}
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
        if os.getenv("VK_REQUIRED", "1").strip().lower() in ("0", "false", "no"):
            return {"status": "disabled", "reason": "VK smoke explicitly disabled"}
        return {"status": "failed", "reason": "VK_TOKEN not set"}
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
        return {"status": "failed", "reason": "SAAS_PUBLIC_URL not set"}
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"status": "failed", "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-http2", "--disable-dev-shm-usage"])
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        )
        try:
            # Streamlit Cloud may return the document shell before the app
            # websocket hydrates. Retry the navigation instead of treating a
            # blank shell as a broken login form.
            last_render = {}
            for attempt in range(1, 4):
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    if (
                        page.get_by_text("AI Agent Content Manager", exact=True).count() > 0
                        or page.get_by_label("Email", exact=True).count() > 0
                        or page.locator('[data-testid="stAppViewContainer"]').count() > 0
                    ):
                        break
                    page.wait_for_timeout(1000)
                last_render = {
                    "attempt": attempt,
                    "url": page.url,
                    "title": page.title(),
                    "body_text": page.locator("body").inner_text(timeout=5000)[:1000],
                    "body_html_len": len(page.locator("body").inner_html(timeout=5000)),
                    "app_container_count": page.locator('[data-testid="stAppViewContainer"]').count(),
                    "email_label_count": page.get_by_label("Email", exact=True).count(),
                }
                if last_render["body_text"] or last_render["app_container_count"] > 0:
                    break
                if attempt < 3:
                    page.reload(wait_until="domcontentloaded", timeout=90000)

            email = os.getenv("E2E_EMAIL", "").strip()
            password = os.getenv("E2E_PASSWORD", "")
            if not email or not password:
                return {"status": "failed", "reason": "E2E credentials not set"}

            # Streamlit Cloud can expose the rendered app in a child frame while
            # the outer document remains only a shell. Search every frame for the
            # actual login controls instead of assuming the top-level document owns them.
            def find_login_frame():
                for frame in page.frames:
                    try:
                        if (
                            frame.get_by_label("Email", exact=True).count() > 0
                            or frame.get_by_text("AI Agent Content Manager", exact=True).count() > 0
                            or frame.locator('[data-testid="stAppViewContainer"]').count() > 0
                        ):
                            return frame
                    except Exception:
                        continue
                return page.main_frame

            login_frame = page.main_frame
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                login_frame = find_login_frame()
                try:
                    if (
                        login_frame.get_by_label("Email", exact=True).count() > 0
                        and login_frame.get_by_label("Пароль", exact=True).count() > 0
                    ):
                        break
                except Exception:
                    pass
                page.wait_for_timeout(1000)

            try:
                login_tab = login_frame.get_by_role("tab", name="Войти", exact=True)
                if login_tab.count() > 0:
                    login_tab.first.click()
            except Exception:
                pass

            email_field = login_frame.get_by_label("Email", exact=True)
            password_field = login_frame.get_by_label("Пароль", exact=True)
            login_buttons = login_frame.locator("button:visible").filter(has_text="Войти")

            deadline = time.monotonic() + 30
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
                "frame_count": len(page.frames),
                "frame_urls": [frame.url for frame in page.frames],
                "email_label_count": email_field.count(),
                "password_label_count": password_field.count(),
                "visible_inputs": login_frame.locator("input:visible").count(),
                "visible_login_buttons": login_buttons.count(),
                "url": page.url,
                "title": page.title(),
                "body_text": page.locator("body").inner_text(timeout=5000)[:1000],
                "body_html_len": len(page.locator("body").inner_html(timeout=5000)),
                "app_container_count": page.locator('[data-testid="stAppViewContainer"]').count(),
                "selected_frame_url": login_frame.url,
                "selected_frame_body_text": login_frame.locator("body").inner_text(timeout=5000)[:1000],
                "last_render": last_render,
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

            # Streamlit buttons can be re-mounted during a rerun. Trigger the
            # native button first, then use Enter/DOM click fallbacks if the
            # password field remains visible. This distinguishes a real auth
            # failure from a missed browser event.
            button = login_buttons.last
            click_error = None
            try:
                button.click(timeout=10000)
            except Exception as exc:
                click_error = str(exc)

            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if login_frame.locator('input[type="password"]:visible').count() == 0:
                    break
                page.wait_for_timeout(500)

            if login_frame.locator('input[type="password"]:visible').count() > 0:
                try:
                    password_field.first.press("Enter", timeout=5000)
                except Exception as exc:
                    click_error = click_error or str(exc)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if login_frame.locator('input[type="password"]:visible').count() == 0:
                        break
                    page.wait_for_timeout(500)

            if login_frame.locator('input[type="password"]:visible').count() > 0:
                try:
                    button.evaluate("(el) => el.click()")
                except Exception as exc:
                    click_error = click_error or str(exc)
                page.wait_for_timeout(5000)

            os.makedirs("artifacts/smoke", exist_ok=True)
            post_login = {
                "url": page.url,
                "title": page.title(),
                "password_visible": login_frame.locator('input[type="password"]:visible').count(),
                "login_button_count": login_frame.locator("button:visible").filter(has_text="Войти").count(),
                "body_text": login_frame.locator("body").inner_text(timeout=5000)[:2000],
                "click_error": click_error,
            }
            page.screenshot(path="artifacts/smoke/authenticated-home.png", full_page=True)

            if post_login["password_visible"] > 0:
                raise RuntimeError(
                    "Authenticated login did not complete: "
                    + json.dumps(post_login, ensure_ascii=False)
                )

            result = login_frame.evaluate("""() => ({
              url: location.href,
              hasWebMcpSdk: !!globalThis.__WEBMCP_TELEMETRY__,
              registered: !!globalThis.__ARSENAL_WEBMCP_READY__
            })""")
            if not result.get("registered"):
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
        report["load_test"] = {"status": "failed", "reason": "SAAS_PUBLIC_URL not set"}

    report["telegram"] = telegram_readonly()
    report["vk"] = vk_readonly()

    try:
        report["webmcp"] = browser_webmcp()
    except Exception as exc:
        report["webmcp"] = {"status": "failed", "error": str(exc)}

    with open("smoke-report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    live_statuses = [report["telegram"], report["vk"], report["webmcp"]]
    live_ok = all(x.get("status") in ("ok", "disabled") for x in live_statuses)
    load_ok = (
        report["load_test"].get("status", "ok") not in ("failed", "skipped")
        and report["load_test"].get("failures", 0) == 0
    )
    return 0 if live_ok and load_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
