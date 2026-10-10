import json
import os
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


BASE_URL = os.getenv(
    "SAAS_PUBLIC_URL",
    "https://arsenal-sport-b3rvpnysmxhvw9wud8wjjd.streamlit.app",
).rstrip("/")
TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "180000"))
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
    """Record the non-browser health result without confusing Streamlit auth redirects with browser availability."""
    url = f"{BASE_URL}/_stcore/health"
    started = time.perf_counter()
    response = requests.get(url, timeout=60, allow_redirects=False)
    latency_ms = round((time.perf_counter() - started) * 1000)
    body = response.text.strip()
    result = {
        "url": url,
        "status": response.status_code,
        "location": response.headers.get("Location", ""),
        "body": body[:500],
        "latency_ms": latency_ms,
    }
    (OUT / "health.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    location = result["location"]
    if response.status_code in (301, 302, 303, 307, 308) and "share.streamlit.io/-/auth/" in location:
        result["warning"] = (
            "Non-browser health request was redirected to Streamlit's auth gateway. "
            "This alone does not establish whether the app is public; continuing with real-browser checks."
        )
        print(f"WARNING: {result['warning']}")
        return
    if response.status_code != 200:
        raise RuntimeError(f"Production health endpoint returned HTTP {response.status_code}: {result}")
    if body.lower() != "ok":
        result["warning"] = (
            "Health endpoint did not return the expected plain-text 'ok'; "
            "continuing to the homepage and real-browser checks."
        )
        print(f"WARNING: {result['warning']}")


def startup_http_probe():
    """Capture a diagnostic homepage response; real-browser checks are authoritative for UI access."""
    url = BASE_URL
    started = time.perf_counter()
    result = {"url": url}
    try:
        response = requests.get(
            url,
            timeout=60,
            allow_redirects=False,
            headers={"User-Agent": "AI-Agent-Content-Manager-Production-Smoke/1.0"},
        )
        body = response.text[:20000]
        result.update({
            "status": response.status_code,
            "location": response.headers.get("Location", ""),
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "content_type": response.headers.get("content-type", ""),
            "server": response.headers.get("server", ""),
            "body_prefix": body,
            "streamlit_markers": {
                "has_streamlit": "streamlit" in body.lower(),
                "has_error": any(x in body.lower() for x in ("exception", "traceback", "error")),
                "has_auth_email": "Email" in body,
                "has_auth_password": "Пароль" in body,
            },
        })
    except Exception as exc:
        result.update({
            "status": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        })
    (OUT / "startup-http.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    location = result.get("location", "")
    if result.get("status") in (301, 302, 303, 307, 308) and "share.streamlit.io/-/auth/" in location:
        print("WARNING: Non-browser homepage request redirected to Streamlit auth gateway; browser matrix will determine UI access.")
        return
    if result.get("status") != 200:
        raise RuntimeError(f"Production application HTTP probe failed: {result}")


def browser_url():
    parts = urlsplit(BASE_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["pw_probe"] = str(int(time.time()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def visible_label_locator(page, label, timeout_ms):
    """Wait for a visible labelled control, rescanning frames as Streamlit attaches them."""
    deadline = time.monotonic() + timeout_ms / 1000
    last_error = None
    while time.monotonic() < deadline:
        contexts = [page.main_frame] + [frame for frame in page.frames if frame != page.main_frame]
        for frame in contexts:
            try:
                locator = frame.get_by_label(label)
                if locator.count() and locator.first.is_visible():
                    return locator.first, frame.url
            except Exception as exc:
                last_error = exc
        page.wait_for_timeout(250)
    raise RuntimeError(
        f"Could not find visible label {label!r} in the page or any attached iframe "
        f"within {timeout_ms} ms. Last error: {last_error}"
    )


def visible_page_text(page):
    """Collect visible text from the top-level page and embedded app frames."""
    chunks = []
    for frame in page.frames:
        try:
            text = frame.locator("body").inner_text(timeout=3000).strip()
            if text:
                chunks.append(text)
        except Exception:
            continue
    return "\n".join(chunks)[:20000]


def run():
    health_check()
    startup_http_probe()
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
                page.goto(browser_url(), wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                item["initial_url"] = page.url
                item["title"] = page.title()
                item["body_prefix"] = visible_page_text(page)
                item["frames"] = [
                    {"url": frame.url, "name": frame.name}
                    for frame in page.frames
                ]
                frame_urls = [frame["url"] for frame in item["frames"]]
                statuspage_detected = (
                    any("statuspage.io/embed/frame" in frame_url for frame_url in frame_urls)
                    or (
                        "Status embed installed" in item["body_prefix"]
                        and "incident or maintenance" in item["body_prefix"]
                    )
                )
                if statuspage_detected and ("Email" not in item["body_prefix"] or "Пароль" not in item["body_prefix"]):
                    raise RuntimeError(
                        "PRODUCTION_STATUSPAGE_INTERSTITIAL: the browser rendered the Statuspage "
                        "embed instead of the application login UI. This is a hosting/deployment/"
                        "access diagnostic, not a selector timeout. "
                        f"initial_url={item['initial_url']!r}; frames={frame_urls[:10]!r}; "
                        f"body_prefix={item['body_prefix'][:1000]!r}"
                    )

                item["content_markers"] = {
                    "has_email": "Email" in item["body_prefix"],
                    "has_password": "Пароль" in item["body_prefix"],
                    "has_exception": any(x in item["body_prefix"].lower() for x in ("exception", "traceback", "error")),
                    "has_streamlit_shell": "hosted with streamlit" in item["body_prefix"].lower(),
                }
                if not item["content_markers"]["has_email"] or not item["content_markers"]["has_password"]:
                    raise RuntimeError(
                        "The expected login labels are missing from visible rendered page text; "
                        "accessible controls alone are not enough to pass acceptance. "
                        f"Rendered text prefix: {item['body_prefix'][:1000]!r}"
                    )
                _, email_frame_url = visible_label_locator(page, "Email", TIMEOUT_MS)
                _, password_frame_url = visible_label_locator(page, "Пароль", 30000)
                rendered_text = visible_page_text(page)
                if "Email" not in rendered_text or "Пароль" not in rendered_text:
                    raise RuntimeError(
                        "The browser found accessible login controls, but the rendered page "
                        "does not contain the expected app login labels. "
                        f"Rendered text prefix: {rendered_text[:1000]!r}"
                    )
                item["login_control_context"] = {
                    "email_frame_url": email_frame_url,
                    "password_frame_url": password_frame_url,
                }
                item["status"] = "PASS"
            except Exception as exc:
                item["status"] = "FAIL"
                item["error"] = str(exc)
                item["url"] = page.url
                item["title"] = page.title()
                item["body"] = visible_page_text(page)
                item["frames"] = [{"url": frame.url, "name": frame.name} for frame in page.frames]
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
