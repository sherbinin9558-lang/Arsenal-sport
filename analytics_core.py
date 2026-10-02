import json
from pathlib import Path
from datetime import datetime

EVENTS_FILE=Path("analytics_events.json")

def load_events():
    if not EVENTS_FILE.exists(): return []
    try: return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    except Exception: return []

def track(event, source="app", product_id="", meta=None):
    events=load_events()
    events.append({"event":event,"source":source,"product_id":product_id,
                   "meta":meta or {},"at":datetime.now().isoformat(timespec="seconds")})
    EVENTS_FILE.write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")

def event_counts(events):
    out={}
    for e in events: out[e.get("event","unknown")]=out.get(e.get("event","unknown"),0)+1
    return out
