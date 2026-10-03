"""Tenant-isolated analytics storage.

This module no longer writes to a repository-wide analytics_events.json.
"""
from datetime import datetime
from saas_core import data_load, data_save

ENTITY = "analytics_events"

def load_events():
    return data_load(ENTITY, [])

def track(event, source="app", product_id="", meta=None):
    events = load_events()
    events.append({
        "event": event,
        "source": source,
        "product_id": str(product_id or ""),
        "meta": meta or {},
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    data_save(ENTITY, events)
    return events[-1]

def event_counts(events):
    out = {}
    for e in events:
        key = e.get("event", "unknown")
        out[key] = out.get(key, 0) + 1
    return out
