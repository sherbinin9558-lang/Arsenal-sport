#!/usr/bin/env python3
"""Optional live P2 verification harness.

No payment is charged and no social post is published by default.
Set explicit environment variables to enable provider/browser checks.
"""
import os, sys, time, json, csv, tempfile, statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def http(url, timeout=15):
    start=time.perf_counter()
    try:
        req=Request(url, headers={"User-Agent":"ArsenalSport-P2-Smoke/1.0"})
        with urlopen(req, timeout=timeout) as r:
            body=r.read(4096)
            return True, r.status, time.perf_counter()-start, body
    except (HTTPError, URLError, TimeoutError) as e:
        return False, getattr(e,"code",0), time.perf_counter()-start, str(e).encode()

def load_test(url, workers=20, requests_count=100):
    lat=[]
    failures=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(http,url,20) for _ in range(requests_count)]
        for f in as_completed(futures):
            ok,_,elapsed,_=f.result()
            lat.append(elapsed)
            failures += not ok
    return {"requests":requests_count,"workers":workers,"failures":int(failures),
            "p50_ms":round(statistics.median(lat)*1000,1),
            "p95_ms":round(sorted(lat)[max(0,int(len(lat)*.95)-1)]*1000,1),
            "max_ms":round(max(lat)*1000,1)}

def telegram_readonly():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    if not token: return {"status":"skipped","reason":"TELEGRAM_BOT_TOKEN not set"}
    ok,status,elapsed,body=http(f"https://api.telegram.org/bot{token}/getMe")
    return {"status":"ok" if ok else "failed","http":status,"latency_ms":round(elapsed*1000,1),
            "body":body.decode("utf-8","replace")[:500]}

def vk_readonly():
    token=os.getenv("VK_TOKEN","").strip()
    if not token: return {"status":"skipped","reason":"VK_TOKEN not set"}
    import urllib.parse
    req=Request(
        "https://api.vk.com/method/users.get",
        data=urllib.parse.urlencode({"access_token": token, "v": "5.199"}).encode(),
        headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"ArsenalSport-P2-Smoke/1.0"},
        method="POST",
    )
    start=time.perf_counter()
    try:
        with urlopen(req, timeout=15) as r:
            body=r.read(4096)
            ok,status=True,r.status
    except (HTTPError, URLError, TimeoutError) as e:
        body=str(e).encode()
        ok,status=False,getattr(e,"code",0)
    elapsed=time.perf_counter()-start
    return {"status":"ok" if ok else "failed","http":status,"latency_ms":round(elapsed*1000,1),
            "body":body.decode("utf-8","replace")[:500]}

def browser_webmcp():
    url=os.getenv("SAAS_PUBLIC_URL","").strip()
    if not url: return {"status":"skipped","reason":"SAAS_PUBLIC_URL not set"}
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"status":"skipped","reason":"playwright not installed"}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        email=os.getenv("E2E_EMAIL","").strip()
        password=os.getenv("E2E_PASSWORD","")
        if not email or not password:
            browser.close()
            return {"status":"skipped","reason":"E2E credentials not set"}
        email_field = page.get_by_label("Email")
        password_field = page.get_by_label("Пароль")
        login_button = page.get_by_role("button", name="Войти")
        if email_field.count() != 1 or password_field.count() != 1 or login_button.count() != 1:
            raise RuntimeError("Authenticated login form was not found.")
        email_field.fill(email)
        password_field.fill(password)
        login_button.click()
        page.wait_for_timeout(5000)
        if page.get_by_role("button", name="Войти").count() > 0:
            raise RuntimeError("Authenticated login did not complete.")
        result=page.evaluate("""() => ({
          url: location.href,
          hasWebMcpSdk: !!globalThis.__WEBMCP_TELEMETRY__,
          registered: !!globalThis.__ARSENAL_WEBMCP_READY__
        })""")
        browser.close()
    if not result.get("registered"):
            raise RuntimeError("WebMCP registration marker was not detected.")
    return {"status":"ok","result":result}

def main():
    report={}
    app_url=os.getenv("SAAS_PUBLIC_URL","").strip()
    if app_url:
        report["load_test"]=load_test(app_url, int(os.getenv("LOAD_WORKERS","20")), int(os.getenv("LOAD_REQUESTS","100")))
    else:
        report["load_test"]={"status":"skipped","reason":"SAAS_PUBLIC_URL not set"}
    report["telegram"]=telegram_readonly()
    report["vk"]=vk_readonly()
    report["webmcp"]=browser_webmcp()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(x.get("status") not in ("failed",) for x in [report["telegram"],report["vk"],report["webmcp"]]) and report["load_test"].get("failures",0)==0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
