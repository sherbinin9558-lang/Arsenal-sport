"""Production operations helpers: provider health, observability, audit and safe automation primitives."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from saas_core import data_load, data_save, tenant_id, current_role, can

ENTITY_AUDIT = "audit_events"
ENTITY_METRICS = "ops_metrics"
MAX_AUDIT = 2000
MAX_METRICS = 5000
AGENT_TTL_MINUTES = 30
MAX_TEXT = 4000
MAX_CAPTION = 2200


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _rows(entity: str):
    return [dict(x) for x in (data_load(entity, []) or []) if isinstance(x, dict)]


def _write(entity: str, rows):
    data_save(entity, rows)


def _write_allowed():
    if not can("write_data"):
        raise PermissionError("Недостаточно прав для изменения данных.")


def _redact(value: str, keep: int = 4) -> str:
    value = str(value or "")
    if len(value) <= keep:
        return "***"
    return value[:keep] + "..." + "*" * min(8, max(3, len(value) - keep))


def _http_json(url: str, headers=None, timeout: int = 15):
    req = Request(url, headers=headers or {"User-Agent": "ArsenalSport-Health/1.0"})
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(4096)
            return True, response.status, time.perf_counter() - started, json.loads(raw.decode("utf-8", "replace"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return False, getattr(exc, "code", 0), time.perf_counter() - started, {"error": type(exc).__name__}


def telegram_health(token: str | None = None) -> dict:
    token = (token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
    if not token:
        return {"status": "skipped", "provider": "telegram", "reason": "credential_not_configured"}
    ok, status, elapsed, body = _http_json(f"https://api.telegram.org/bot{token}/getMe")
    valid = bool(ok and body.get("ok") is True and body.get("result", {}).get("is_bot") is True)
    result = {"status": "ok" if valid else "failed", "provider": "telegram",
              "http": status, "latency_ms": round(elapsed * 1000, 1)}
    if valid:
        result["bot_id"] = body.get("result", {}).get("id")
        result["username"] = body.get("result", {}).get("username")
    else:
        result["error"] = "telegram_credentials_rejected"
    return result


def vk_health(token: str | None = None) -> dict:
    token = (token if token is not None else os.getenv("VK_TOKEN", "")).strip()
    if not token:
        return {"status": "skipped", "provider": "vk", "reason": "credential_not_configured"}
    url = "https://api.vk.com/method/users.get?access_token=" + token + "&v=5.199"
    ok, status, elapsed, body = _http_json(url)
    valid = bool(ok and not body.get("error") and isinstance(body.get("response"), list))
    result = {"status": "ok" if valid else "failed", "provider": "vk",
              "http": status, "latency_ms": round(elapsed * 1000, 1)}
    if valid:
        result["api_version"] = "5.199"
    else:
        result["error"] = "vk_credentials_rejected"
    return result


def provider_health() -> dict:
    return {"checked_at": now_iso(), "telegram": telegram_health(), "vk": vk_health()}


def audit_event(action: str, target: str = "", outcome: str = "success", details: dict | None = None) -> dict:
    """Write a bounded tenant-scoped audit record; never stores credentials."""
    _write_allowed()
    row = {
        "id": f"audit_{int(time.time() * 1000)}_{abs(hash((action, target, time.time_ns()))) % 1000000}",
        "tenant_id": str(tenant_id()), "actor_role": str(current_role() or ""),
        "action": str(action)[:120], "target": str(target)[:200],
        "outcome": str(outcome)[:40], "details": dict(details or {}),
        "created_at": now_iso(),
    }
    rows = _rows(ENTITY_AUDIT)
    rows.insert(0, row)
    _write(ENTITY_AUDIT, rows[:MAX_AUDIT])
    return row


def record_metric(name: str, value: float = 1.0, tags: dict | None = None) -> dict:
    _write_allowed()
    row = {"id": f"metric_{int(time.time()*1000)}_{abs(hash(time.time_ns())) % 1000000}",
           "tenant_id": str(tenant_id()), "name": str(name)[:120],
           "value": float(value), "tags": dict(tags or {}), "created_at": now_iso()}
    rows = _rows(ENTITY_METRICS)
    rows.insert(0, row)
    _write(ENTITY_METRICS, rows[:MAX_METRICS])
    return row


def observability_snapshot() -> dict:
    events = _rows(ENTITY_AUDIT)
    metrics = _rows(ENTITY_METRICS)
    by_action = Counter(str(x.get("action")) for x in events)
    errors = sum(str(x.get("outcome")).lower() in {"error", "failed"} for x in events)
    return {"audit_events": len(events), "metrics": len(metrics),
            "audit_errors": errors, "top_actions": dict(by_action.most_common(10)),
            "latest_event_at": events[0].get("created_at") if events else None}


def validate_agent_payload(action_type: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Параметры AI-действия должны быть объектом.")
    allowed = {
        "create_task": {"title","description","assignee","priority","due_date"},
        "create_notification": {"title","body"},
        "queue_instagram_draft": {"caption","media_ref","product_id","scheduled_at"},
    }
    fields = allowed.get(action_type)
    if fields is None:
        raise ValueError("Действие не входит в безопасный allowlist.")
    unknown = set(payload) - fields
    if unknown:
        raise ValueError("AI-действие содержит запрещённые поля.")
    clean = dict(payload)
    for key, value in clean.items():
        if isinstance(value, str) and len(value) > MAX_TEXT:
            raise ValueError(f"Поле {key} слишком длинное.")
    if action_type == "queue_instagram_draft":
        caption = str(clean.get("caption", "")).strip()
        if not caption:
            raise ValueError("Instagram-черновик требует подпись.")
        if len(caption) > MAX_CAPTION:
            raise ValueError("Подпись Instagram превышает безопасный лимит.")
    return clean


def agent_is_expired(created_at: str, ttl_minutes: int = AGENT_TTL_MINUTES) -> bool:
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - created > timedelta(minutes=ttl_minutes)
    except (TypeError, ValueError):
        return True
