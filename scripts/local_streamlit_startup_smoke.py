"""Start the app locally and capture Streamlit startup failures before deployment."""
import json, os, signal, subprocess, sys, time
from pathlib import Path
import requests

OUT = Path("artifacts/local-startup"); OUT.mkdir(parents=True, exist_ok=True)
PORT = int(os.getenv("STARTUP_SMOKE_PORT", "8502")); TIMEOUT = int(os.getenv("STARTUP_SMOKE_TIMEOUT", "45"))

def run():
    env=os.environ.copy(); env.setdefault("SAAS_PUBLIC_URL", f"http://localhost:{PORT}")
    cmd=[sys.executable,"-m","streamlit","run","app.py","--server.headless=true",f"--server.port={PORT}","--browser.gatherUsageStats=false"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env)
    lines=[]; started=time.perf_counter(); health=None
    try:
        while time.perf_counter()-started<TIMEOUT:
            if proc.stdout:
                line=proc.stdout.readline()
                if line:
                    lines.append(line.rstrip()); lines=lines[-400:]
            try:
                r=requests.get(f"http://127.0.0.1:{PORT}/_stcore/health",timeout=2)
                health={"status":r.status_code,"body":r.text.strip()[:500]}
                if health["status"]==200 and health["body"]=="ok": break
            except requests.RequestException: pass
            if proc.poll() is not None: break
            time.sleep(.5)
        result={"returncode":proc.poll(),"health":health,"duration_ms":round((time.perf_counter()-started)*1000),"log_tail":lines[-200:]}
        (OUT/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not health or health["status"]!=200 or health["body"]!="ok": raise SystemExit("Local Streamlit startup/health check failed")
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: proc.kill()

if __name__=="__main__": run()
