import json
import os
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("SAAS_PUBLIC_URL", "https://arsenal-sport-b3rvpnysmxhvw9wud8wjjd.streamlit.app").rstrip("/")
OUT = Path("artifacts/playwright-diagnostic")
OUT.mkdir(parents=True, exist_ok=True)


def log(message):
    print(message, flush=True)


def http_probe(path, filename):
    url = f"{BASE_URL}{path}"
    started = time.perf_counter()
    result = {"url": url}
    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "AI-Content-Manager-Playwright-Diagnostic/1.0"})
        result.update(status=response.status_code, latency_ms=round((time.perf_counter() - started) * 1000),
                      content_type=response.headers.get("content-type", ""), server=response.headers.get("server", ""),
                      body_prefix=response.text[:5000])
        log(f"HTTP {path}: status={response.status_code}, latency_ms={result['latency_ms']}, content_type={result['content_type']!r}")
    except Exception as exc:
        result.update(status=0, error=f"{type(exc).__name__}: {exc}",
                      latency_ms=round((time.perf_counter() - started) * 1000))
        log(f"HTTP {path} ERROR: {result['error']}")
    (OUT / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    log(f"DIAGNOSTIC START url={BASE_URL}")
    health = http_probe("/_stcore/health", "health.json")
    homepage = http_probe("/", "homepage.json")
    result = {
        "base_url": BASE_URL,
        "health": {k: v for k, v in health.items() if k != "body_prefix"},
        "homepage": {k: v for k, v in homepage.items() if k != "body_prefix"},
        "browser": {},
    }

    with sync_playwright() as pw:
        log("Launching Chromium")
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors, page_errors, request_failures, failed_responses, websocket_events = [], [], [], [], []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: request_failures.append({"url": req.url, "method": req.method, "failure": req.failure}))
        page.on("response", lambda response: failed_responses.append({"status": response.status, "url": response.url}) if response.status >= 400 else None)

        def record_websocket(ws):
            websocket_events.append({"url": ws.url, "event": "created"})
            ws.on("socketerror", lambda error: websocket_events.append({"url": ws.url, "event": "error", "error": str(error)}))
            ws.on("close", lambda: websocket_events.append({"url": ws.url, "event": "closed"}))
        page.on("websocket", record_websocket)

        target = f"{BASE_URL}/?pw_diagnostic={int(time.time())}"
        log(f"Navigating to {target}")
        started = time.perf_counter()
        try:
            response = page.goto(target, wait_until="domcontentloaded", timeout=60000)
            result["browser"]["navigation_status"] = response.status if response else None
            log(f"DOMCONTENTLOADED status={result['browser']['navigation_status']} elapsed_ms={round((time.perf_counter()-started)*1000)}")
        except Exception as exc:
            result["browser"]["navigation_error"] = f"{type(exc).__name__}: {exc}"
            log(f"NAVIGATION ERROR: {result['browser']['navigation_error']}")

        # Capture each attached document independently. The screenshot/body text
        # alone cannot prove that an actual form control exists or is label-associated.
        result["browser"]["frames"] = []
        for index, frame in enumerate(page.frames):
            frame_info = {"index": index, "url": frame.url, "name": frame.name}
            try:
                frame_info["body_text"] = frame.locator("body").inner_text(timeout=5000)[:8000]
            except Exception as exc:
                frame_info["body_error"] = f"{type(exc).__name__}: {exc}"
            try:
                html = frame.content()
                frame_info["html_length"] = len(html)
                (OUT / f"frame-{index}.html").write_text(html, encoding="utf-8")
            except Exception as exc:
                frame_info["html_error"] = f"{type(exc).__name__}: {exc}"
            try:
                frame_info["controls"] = frame.locator("input, textarea, select, [contenteditable='true']").evaluate_all(
                    """els => els.map((el, index) => {
                        const rect = el.getBoundingClientRect();
                        const style = getComputedStyle(el);
                        const labels = el.labels ? Array.from(el.labels).map(label => label.innerText) : [];
                        return {
                            index, tag: el.tagName.toLowerCase(),
                            type: el.getAttribute('type'), id: el.id || null,
                            name: el.getAttribute('name'), placeholder: el.getAttribute('placeholder'),
                            ariaLabel: el.getAttribute('aria-label'),
                            ariaLabelledby: el.getAttribute('aria-labelledby'),
                            labels, role: el.getAttribute('role'),
                            className: typeof el.className === 'string' ? el.className : null,
                            valuePresent: Boolean(el.value),
                            visible: rect.width > 0 && rect.height > 0 &&
                                style.visibility !== 'hidden' && style.display !== 'none',
                            rect: {x: Math.round(rect.x), y: Math.round(rect.y),
                                   width: Math.round(rect.width), height: Math.round(rect.height)}
                        };
                    })"""
                )
            except Exception as exc:
                frame_info["controls_error"] = f"{type(exc).__name__}: {exc}"
            result["browser"]["frames"].append(frame_info)

        try:
            result["browser"]["iframe_elements"] = page.locator("iframe").evaluate_all(
                "(els) => els.map((el) => ({src: el.src, title: el.title, name: el.name, sandbox: el.getAttribute('sandbox')}))"
            )
        except Exception as exc:
            result["browser"]["iframe_inspection_error"] = f"{type(exc).__name__}: {exc}"

        # Compare semantic and structural locators in every document. Record
        # counts/visibility only; do not enter or submit credentials.
        locator_diagnostics = []
        for frame_index, frame in enumerate(page.frames):
            for selector_name, selector in [
                ("label:Email", 'input[aria-label="Email"]'),
                ("placeholder:Email", 'input[placeholder="Email"]'),
                ("name:email", 'input[name="email"]'),
                ("type:email", 'input[type="email"]'),
                ("all-inputs", "input"),
                ("label-text", "label"),
            ]:
                try:
                    loc = frame.locator(selector)
                    count = loc.count()
                    visible_count = sum(1 for i in range(count) if loc.nth(i).is_visible())
                    locator_diagnostics.append({
                        "frame_index": frame_index, "frame_url": frame.url,
                        "selector_name": selector_name, "selector": selector,
                        "count": count, "visible_count": visible_count
                    })
                except Exception as exc:
                    locator_diagnostics.append({
                        "frame_index": frame_index, "frame_url": frame.url,
                        "selector_name": selector_name, "selector": selector,
                        "error": f"{type(exc).__name__}: {exc}"
                    })
        result["browser"]["locator_diagnostics"] = locator_diagnostics
        email_locator = None
        email_context = None
        for frame in page.frames:
            try:
                candidate = frame.get_by_label("Email")
                candidate.wait_for(state="visible", timeout=1500)
                email_locator, email_context = candidate, frame.url
                break
            except Exception:
                continue
        result["browser"]["email_visible"] = email_locator is not None
        result["browser"]["email_context"] = email_context
        result["browser"]["label_locator_failed_but_input_exists"] = (
            email_locator is None and any(
                control.get("tag") == "input" and control.get("visible")
                for frame in result["browser"]["frames"]
                for control in frame.get("controls", [])
            )
        )
        log("CONTROL SUMMARY: " + json.dumps({
            "frames": [{"index": f.get("index"), "url": f.get("url"),
                        "controls": f.get("controls", []),
                        "controls_error": f.get("controls_error")}
                       for f in result["browser"]["frames"]],
            "locator_diagnostics": locator_diagnostics,
            "email_visible": result["browser"]["email_visible"],
            "email_context": email_context
        }, ensure_ascii=False))

        try:
            result["browser"]["title"] = page.title()
            result["browser"]["url"] = page.url
            result["browser"]["body_text"] = page.locator("body").inner_text(timeout=5000)[:12000]
        except Exception as exc:
            result["browser"]["body_read_error"] = f"{type(exc).__name__}: {exc}"

        try:
            html = page.content()
            (OUT / "page.html").write_text(html, encoding="utf-8")
            result["browser"]["html_length"] = len(html)
            log(f"HTML captured: {len(html)} characters")
            log("=== HTML SNAPSHOT (first 12000 chars) ===")
            log(html[:12000])
            log("=== END HTML SNAPSHOT ===")
        except Exception as exc:
            result["browser"]["html_capture_error"] = f"{type(exc).__name__}: {exc}"
            log(f"HTML CAPTURE ERROR: {result['browser']['html_capture_error']}")

        result["browser"].update(console_errors=console_errors[-100:], page_errors=page_errors[-100:],
                                 request_failures=request_failures[-100:], http_error_responses=failed_responses[-100:],
                                 websocket_events=websocket_events[-100:])
        log("=== BROWSER DIAGNOSTICS ===")
        log(json.dumps(result["browser"], ensure_ascii=False, indent=2))
        try:
            page.screenshot(path=str(OUT / "page.png"), full_page=True)
        except Exception as exc:
            log(f"SCREENSHOT ERROR: {exc}")
        browser.close()

    (OUT / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["browser"].get("email_visible"):
        raise SystemExit("Diagnostic failed: login UI did not render; inspect report and page.html artifact")
    log("DIAGNOSTIC PASS: login UI rendered")


if __name__ == "__main__":
    main()
