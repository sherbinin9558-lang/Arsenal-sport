"""Deterministic MAX AI-operator orchestration layer.

MAX is deliberately confirmation-gated: read operations can run immediately,
while any operation that mutates tenant data requires explicit approval.
Every operator action is also metered for commercial unit economics.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Optional

READ = "read"
WRITE = "write"

ACTIONS = {
    "store_status": {"mode": READ, "label": "Проверить состояние магазина"},
    "low_stock": {"mode": READ, "label": "Проверить дефицитные товары"},
    "content_today": {"mode": READ, "label": "Проверить контент на сегодня"},
    "sales_summary": {"mode": READ, "label": "Показать продажи и конверсию"},
    "prepare_today": {"mode": WRITE, "label": "Подготовить контент на сегодня"},
    "create_7_day_plan": {"mode": WRITE, "label": "Создать контент-план на 7 дней"},
    "refresh_analysis": {"mode": READ, "label": "Обновить анализ магазина"},
    "quick_content_plan": {"mode": WRITE, "label": "Создать 7 идей контента"},
    "max_content_suggest": {"mode": WRITE, "label": "Добавить идеи в контент-план"},
    "auto_match_photos": {"mode": WRITE, "label": "Привязать фото к товарам"},
    "auto_content": {"mode": WRITE, "label": "Создать контент"},
    "auto_30_day_plan": {"mode": WRITE, "label": "Создать 30-дневный контент-план"},
    "auto_bulk_apply": {"mode": WRITE, "label": "Применить изменения к товарам"},
    "auto_stock_save": {"mode": WRITE, "label": "Сохранить остатки"},
    "auto_run_all": {"mode": WRITE, "label": "Запустить автоматизацию"},
    "crm_update_status": {"mode": WRITE, "label": "Изменить статус заявки"},
    "crm_add_note": {"mode": WRITE, "label": "Добавить заметку в CRM"},
    "create_order": {"mode": WRITE, "label": "Создать заказ"},
    "update_order_status": {"mode": WRITE, "label": "Изменить статус заказа"},
    "account_auto_renew": {"mode": WRITE, "label": "Изменить автопродление"},
    "account_plan_request": {"mode": WRITE, "label": "Запросить смену тарифа"},
    "team_set_role": {"mode": WRITE, "label": "Изменить роль сотрудника"},
    "team_invite": {"mode": WRITE, "label": "Создать приглашение сотруднику"},
    "billing_tbank_checkout": {"mode": WRITE, "label": "Создать платёж Т‑Банк"},
    "billing_yookassa_checkout": {"mode": WRITE, "label": "Создать платёж ЮKassa"},
    "account_save_settings": {"mode": WRITE, "label": "Сохранить настройки магазина"},
}

_PATTERNS = (
    ("low_stock", r"(остат|заканч|дефицит|склад)"),
    # Match explicit write intent before the broader "content today" read query.
    ("prepare_today", r"(подготов|сделай).*(контент|пост).*(сегодня|на сегодня)"),
    ("content_today", r"(контент|пост).*(сегодня)"),
    ("sales_summary", r"(продаж|выручк|заказ|конверси)"),
    ("create_7_day_plan", r"(создай|сделай).*(контент|план).*(7|недел)"),
    ("refresh_analysis", r"(обнови|анализ).*(магазин|данн)"),
)


@dataclass(frozen=True)
class ActionPlan:
    action: str
    mode: str
    label: str
    reason: str
    requires_confirmation: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", str(command or "").strip().lower())


def resolve_action(command: str) -> Optional[str]:
    text = normalize_command(command)
    for action, pattern in _PATTERNS:
        if text and re.search(pattern, text, re.I):
            return action
    return None


def plan_action(command: str) -> ActionPlan:
    action = resolve_action(command)
    if not action:
        return ActionPlan(
            "unknown",
            READ,
            "Уточнить задачу",
            "Неоднозначная команда.",
            False,
        )
    meta = ACTIONS[action]
    return ActionPlan(
        action,
        meta["mode"],
        meta["label"],
        "Распознано по команде.",
        meta["mode"] == WRITE,
    )


def can_execute(plan: ActionPlan, approved: bool = False) -> bool:
    return plan.action in ACTIONS and (plan.mode == READ or approved)


def execute_write(
    action: str,
    approved: bool,
    operation,
    *,
    actor: str = "MAX",
    details: Optional[dict] = None,
) -> Dict[str, Any]:
    """Single confirmation/audit boundary for MAX write operations."""
    plan = ActionPlan(
        action,
        ACTIONS.get(action, {}).get("mode", WRITE),
        ACTIONS.get(action, {}).get("label", action),
        "MAX write boundary",
        True,
    )
    if not can_execute(plan, approved):
        return {"ok": False, "status": "not_approved", "action": action}
    result = operation()
    event = audit_event(action, "completed", actor=actor, details=details)
    return {"ok": True, "status": "completed", "action": action, "result": result, "audit": event}


def build_business_snapshot(
    products: Iterable[dict],
    leads: Iterable[dict],
    orders: Iterable[dict],
    plan: Iterable[dict],
) -> Dict[str, Any]:
    products = list(products or [])
    leads = list(leads or [])
    orders = list(orders or [])
    content = list(plan or [])
    active = [
        x for x in orders
        if str(x.get("status", "")) not in {"Завершён", "Отменён"}
    ]
    revenue = 0.0
    for row in orders:
        try:
            revenue += float(row.get("amount", row.get("total", 0)) or 0)
        except (TypeError, ValueError):
            pass
    return {
        "products": len(products),
        "leads": len(leads),
        "orders": len(orders),
        "active_orders": len(active),
        "content_items": len(content),
        "revenue": round(revenue, 2),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def audit_event(
    action: str,
    status: str,
    actor: str = "",
    details: Optional[dict] = None,
) -> Dict[str, Any]:
    event = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": str(action),
        "status": str(status),
        "actor": str(actor or "MAX"),
        "details": dict(details or {}),
    }
    try:
        from ai_usage import record_ai_usage
        record_ai_usage(
            f"max.{event['action']}",
            provider="local",
            model="deterministic",
            request_count=1,
            metadata={"status": event["status"]},
        )
    except Exception:
        pass
    return event
