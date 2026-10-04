"""Production-grade P3 business layer.

All external side effects are approval-gated. The module is deliberately free-first:
it uses the existing tenant data layer and does not require a paid AI API.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import uuid
import re
from typing import Any, Iterable

from saas_core import data_load, data_save, tenant_id, current_role, can

ENTITY_TASKS = "tasks"
ENTITY_NOTIFICATIONS = "notifications"
ENTITY_AGENT_ACTIONS = "agent_actions"
ENTITY_INSTAGRAM_QUEUE = "instagram_queue"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _rows(entity: str) -> list[dict]:
    rows = data_load(entity, [])
    return [dict(x) for x in rows if isinstance(x, dict)]


def _write(entity: str, rows: list[dict]) -> None:
    data_save(entity, rows)


def _write_allowed() -> None:
    if not can("write_data"):
        raise PermissionError("Недостаточно прав для изменения данных.")


def _approval_allowed() -> None:
    role = str(current_role() or "").lower()
    if role not in {"owner", "admin", "manager"}:
        raise PermissionError("Подтверждать AI-действия могут только владелец, администратор или менеджер.")


# ---------- Notifications ----------

def create_notification(title: str, body: str, level: str = "info", link: str = "", record_id: str = "") -> dict:
    _write_allowed()
    title = str(title or "").strip()
    body = str(body or "").strip()
    if not title or not body:
        raise ValueError("Заголовок и текст уведомления обязательны.")
    rows = _rows(ENTITY_NOTIFICATIONS)
    if record_id:
        existing = next((x for x in rows if str(x.get("_saas_record_id")) == str(record_id) or str(x.get("id")) == f"ntf_{record_id}"), None)
        if existing:
            return existing
    row = {
        "id": f"ntf_{record_id}" if record_id else _id("ntf"), "tenant_id": str(tenant_id()), "title": str(title).strip(),
        "body": str(body).strip(), "level": level if level in {"info","success","warning","error"} else "info",
        "link": str(link or ""), "read": False, "created_at": _now(),
    }
    if record_id:
        row["_saas_record_id"] = str(record_id)
    rows.insert(0, row)
    _write(ENTITY_NOTIFICATIONS, rows[:500])
    return row


def notifications(unread_only: bool = False, limit: int = 50) -> list[dict]:
    rows = _rows(ENTITY_NOTIFICATIONS)
    if unread_only:
        rows = [x for x in rows if not x.get("read")]
    return rows[:max(1, min(int(limit), 200))]


def mark_notification_read(notification_id: str) -> bool:
    _write_allowed()
    rows = _rows(ENTITY_NOTIFICATIONS)
    changed = False
    for row in rows:
        if str(row.get("id")) == str(notification_id):
            row["read"] = True
            row["read_at"] = _now()
            changed = True
            break
    if changed:
        _write(ENTITY_NOTIFICATIONS, rows)
    return changed


# ---------- Team tasks ----------

def create_task(title: str, description: str = "", assignee: str = "", priority: str = "Обычный",
                due_date: str = "", entity_type: str = "", entity_id: str = "", record_id: str = "") -> dict:
    _write_allowed()
    title = str(title or "").strip()
    if not title:
        raise ValueError("Название задачи не может быть пустым.")
    priority = priority if priority in {"Низкий","Обычный","Высокий","Срочно"} else "Обычный"
    rows = _rows(ENTITY_TASKS)
    if record_id:
        existing = next((x for x in rows if str(x.get("_saas_record_id")) == str(record_id) or str(x.get("id")) == f"task_{record_id}"), None)
        if existing:
            return existing
    row = {
        "id": f"task_{record_id}" if record_id else _id("task"), "tenant_id": str(tenant_id()), "title": str(title).strip(),
        "description": str(description).strip(), "assignee": str(assignee).strip(),
        "priority": priority, "due_date": str(due_date).strip(), "status": "Открыта",
        "entity_type": str(entity_type), "entity_id": str(entity_id), "created_at": _now(),
        "created_by": str(__import__("streamlit").session_state.get("saas_user_id","")),
    }
    if record_id:
        row["_saas_record_id"] = str(record_id)
    rows.insert(0, row)
    _write(ENTITY_TASKS, rows[:5000])
    return row


def update_task(task_id: str, **changes: Any) -> dict | None:
    _write_allowed()
    allowed = {"title","description","assignee","priority","due_date","status","entity_type","entity_id"}
    rows = _rows(ENTITY_TASKS)
    found = None
    for row in rows:
        if str(row.get("id")) == str(task_id):
            for key, value in changes.items():
                if key in allowed:
                    row[key] = value
            row["updated_at"] = _now()
            found = row
            break
    if found:
        _write(ENTITY_TASKS, rows)
    return found


def task_metrics() -> dict:
    rows = _rows(ENTITY_TASKS)
    counts = Counter(str(x.get("status","Открыта")) for x in rows)
    today = datetime.now(timezone.utc).date()
    overdue = 0
    for row in rows:
        if str(row.get("status","Открыта")) == "Готово":
            continue
        due = str(row.get("due_date","")).strip()
        if due:
            try:
                if datetime.fromisoformat(due.replace("Z","+00:00")).date() < today:
                    overdue += 1
            except ValueError:
                try:
                    if datetime.strptime(due[:10], "%Y-%m-%d").date() < today:
                        overdue += 1
                except ValueError:
                    pass
    return {"total": len(rows), "open": sum(x.get("status") != "Готово" for x in rows),
            "overdue": overdue, "by_status": dict(counts)}


# ---------- Deeper CRM intelligence ----------

def enrich_lead(lead: dict) -> dict:
    lead = dict(lead or {})
    text = " ".join(str(lead.get(k,"")) for k in ("name","message","product","comment")).lower()
    score = 0
    if any(x in text for x in ("цена","стоимость","купить","заказать")): score += 35
    if any(x in text for x in ("размер","размеры","м","l","xl","42","44","46")): score += 20
    if lead.get("phone") or lead.get("telegram") or lead.get("contact"): score += 20
    if lead.get("product"): score += 15
    if lead.get("status") in ("Новый","В работе"): score += 10
    lead["lead_score"] = min(100, score)
    lead["intent"] = "Горячий" if score >= 70 else ("Тёплый" if score >= 40 else "Холодный")
    lead["next_action"] = (
        "Связаться сегодня и предложить конкретный товар/размер." if score >= 70
        else "Уточнить потребность, размер и город." if score >= 40
        else "Дать полезную информацию и мягкий CTA."
    )
    return lead


def crm_pipeline(leads: Iterable[dict]) -> dict:
    enriched = [enrich_lead(x) for x in leads]
    statuses = Counter(str(x.get("status","Новый")) for x in enriched)
    intents = Counter(str(x.get("intent","Холодный")) for x in enriched)
    return {"total": len(enriched), "statuses": dict(statuses), "intents": dict(intents),
            "hot": sum(x.get("intent") == "Горячий" for x in enriched),
            "avg_score": round(sum(x.get("lead_score",0) for x in enriched) / len(enriched), 1) if enriched else 0.0}



def run_notification_automation(products: list[dict], leads: list[dict], orders: list[dict], plan: list[dict]) -> list[dict]:
    """Create deduplicated operational notifications from observed store data."""
    if not can("write_data"):
        return []
    existing = _rows(ENTITY_NOTIFICATIONS)
    keys = {str(x.get("automation_key")) for x in existing}
    created = []
    for product in products:
        try:
            stock = int(product.get("stock", product.get("total_stock", 0)) or 0)
        except (TypeError, ValueError):
            stock = 0
        if 0 < stock <= 2:
            key = f"low-stock:{product.get('_saas_record_id') or product.get('article') or product.get('name')}"
            if key not in keys:
                row = create_notification("Низкий остаток", f"«{product.get('name','Товар')}» — осталось {stock} шт.", "warning", record_id=f"automation_low_stock_{hashlib.sha256(key.encode()).hexdigest()[:24]}")
                row["automation_key"] = key
                created.append(row); keys.add(key)
    for lead in [enrich_lead(x) for x in leads]:
        if lead.get("intent") == "Горячий":
            key = f"hot-lead:{lead.get('_saas_record_id') or lead.get('id') or lead.get('name')}"
            if key not in keys:
                row = create_notification("Горячий лид", f"{lead.get('name') or lead.get('product') or 'Новый клиент'}: {lead.get('next_action')}", "success", record_id=f"automation_hot_lead_{hashlib.sha256(key.encode()).hexdigest()[:24]}")
                row["automation_key"] = key
                created.append(row); keys.add(key)
    if created:
        rows = _rows(ENTITY_NOTIFICATIONS)
        by_id = {x["id"]: x for x in created}
        for row in rows:
            if row.get("id") in by_id:
                row["automation_key"] = by_id[row["id"]].get("automation_key")
        _write(ENTITY_NOTIFICATIONS, rows)
    return created

# ---------- Safe AI-agent actions ----------

ACTION_REGISTRY = {
    "create_task": {"label": "Создать задачу", "side_effect": "internal"},
    "create_notification": {"label": "Создать уведомление", "side_effect": "internal"},
    "queue_instagram_draft": {"label": "Поставить Instagram-черновик", "side_effect": "internal"},
}


def propose_agent_action(action_type: str, payload: dict) -> dict:
    if action_type not in ACTION_REGISTRY:
        raise ValueError("Действие не разрешено.")
    return {
        "id": _id("act"), "tenant_id": str(tenant_id()), "action": action_type,
        "payload": dict(payload or {}), "status": "pending_approval", "created_at": _now(),
        "created_by": str(__import__("streamlit").session_state.get("saas_user_id","")),
    }


def queue_agent_action(action_type: str, payload: dict) -> dict:
    _write_allowed()
    row = propose_agent_action(action_type, payload)
    rows = _rows(ENTITY_AGENT_ACTIONS)
    rows.insert(0, row)
    _write(ENTITY_AGENT_ACTIONS, rows[:1000])
    return row


def approve_agent_action(action_id: str, execute: bool = False) -> dict | None:
    _write_allowed()
    _approval_allowed()
    rows = _rows(ENTITY_AGENT_ACTIONS)
    target = next((x for x in rows if str(x.get("id")) == str(action_id)), None)
    if not target:
        return None
    if target.get("status") != "pending_approval":
        return target
    target["status"] = "approved"
    target["approved_at"] = _now()
    if execute:
        result = execute_agent_action(target)
        target["status"] = result.get("status", "executed")
        target["result"] = result
        target["executed_at"] = _now()
    _write(ENTITY_AGENT_ACTIONS, rows)
    return target


def execute_agent_action(action: dict) -> dict:
    """Execute only internal, reversible actions. External publishing/payment is never implicit."""
    kind = action.get("action")
    payload = action.get("payload") or {}
    if kind == "create_task":
        row = create_task(payload.get("title","AI-задача"), payload.get("description",""),
                          payload.get("assignee",""), payload.get("priority","Обычный"),
                          payload.get("due_date",""), record_id=f"agent_task_{action.get('id')}")
        return {"status": "executed", "task_id": row["id"]}
    if kind == "create_notification":
        row = create_notification(payload.get("title","AI уведомление"), payload.get("body",""), link=f"agent_action:{action.get('id')}", record_id=f"agent_notification_{action.get('id')}")
        return {"status": "executed", "notification_id": row["id"]}
    if kind == "queue_instagram_draft":
        row = queue_instagram_draft(payload.get("caption",""), payload.get("media_ref",""),
                                    payload.get("product_id",""), record_id=f"agent_instagram_{action.get('id')}")
        return {"status": "executed", "draft_id": row["id"]}
    return {"status": "blocked", "reason": "Внешнее действие требует отдельного подтверждения и подключённого провайдера."}


# ---------- Instagram automation (safe queue, not silent publishing) ----------

def queue_instagram_draft(caption: str, media_ref: str = "", product_id: str = "", record_id: str = "") -> dict:
    _write_allowed()
    caption = str(caption or "").strip()
    if not caption:
        raise ValueError("Подпись Instagram не может быть пустой.")
    rows = _rows(ENTITY_INSTAGRAM_QUEUE)
    if record_id:
        existing = next((x for x in rows if str(x.get("_saas_record_id")) == str(record_id) or str(x.get("id")) == f"ig_{record_id}"), None)
        if existing:
            return existing
    row = {"id": f"ig_{record_id}" if record_id else _id("ig"), "tenant_id": str(tenant_id()), "caption": str(caption).strip(),
           "media_ref": str(media_ref), "product_id": str(product_id), "status": "Черновик",
           "created_at": _now()}
    if record_id:
        row["_saas_record_id"] = str(record_id)
    rows.insert(0, row)
    _write(ENTITY_INSTAGRAM_QUEUE, rows[:1000])
    return row


def instagram_queue() -> list[dict]:
    return _rows(ENTITY_INSTAGRAM_QUEUE)[:100]


# ---------- Analytics ----------

def advanced_analytics(products: list[dict], leads: list[dict], orders: list[dict], plan: list[dict]) -> dict:
    revenue = sum(float(str(x.get("amount",0)).replace(" ","").replace(",",".").replace("₽","") or 0)
                  for x in orders if x.get("status") != "Отменён")
    completed = sum(x.get("status") == "Завершён" for x in orders)
    published = sum(x.get("status") == "Опубликовано" for x in plan)
    return {
        "catalog": len(products), "leads": len(leads), "orders": len(orders),
        "published": published, "revenue": revenue, "completed_orders": completed,
        "lead_to_order": round(len(orders)/len(leads)*100,2) if leads else 0.0,
        "order_completion": round(completed/len(orders)*100,2) if orders else 0.0,
        "revenue_per_order": round(revenue/len(orders),2) if orders else 0.0,
        "top_sources": dict(Counter(str(x.get("source","unknown")) for x in leads)),
    }
