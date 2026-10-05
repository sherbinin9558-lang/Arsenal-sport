"""Deterministic MAX AI-operator orchestration layer.

This module deliberately contains no network calls and no model/API dependency.
It converts plain-language requests into safe, reviewable action plans.
Write actions are never executed by this layer without explicit approval.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Optional

READ = "read"
WRITE = "write"

ACTIONS: Dict[str, Dict[str, str]] = {
    "store_status": {"mode": READ, "label": "Проверить состояние магазина"},
    "low_stock": {"mode": READ, "label": "Проверить дефицитные товары"},
    "content_today": {"mode": READ, "label": "Проверить контент на сегодня"},
    "sales_summary": {"mode": READ, "label": "Показать продажи и конверсию"},
    "create_7_day_plan": {"mode": WRITE, "label": "Создать контент-план на 7 дней"},
    "refresh_analysis": {"mode": READ, "label": "Обновить анализ магазина"},
}

_PATTERNS = (
    ("low_stock", r"(остат|заканч|дефицит|мало\s+товар|склад)"),
    ("content_today", r"(контент|публикац|пост).*(сегодня|на\s+сегодня)"),
    ("sales_summary", r"(продаж|выручк|заказ|конверси|воронк)"),
    ("create_7_day_plan", r"(создай|сделай|сформируй|подготовь).*(контент|план).*(7|семь|недел)"),
    ("refresh_analysis", r"(обнови|пересчитай|проанализируй|анализ).*(магазин|данн|состояни)"),
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
    if not text:
        return None
    for action, pattern in _PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return action
    return None


def plan_action(command: str) -> ActionPlan:
    action = resolve_action(command)
    if not action:
        return ActionPlan(
            action="unknown",
            mode=READ,
            label="Уточнить задачу",
            reason="MAX не смог однозначно определить безопасное действие.",
            requires_confirmation=False,
        )
    meta = ACTIONS[action]
    return ActionPlan(
        action=action,
        mode=meta["mode"],
        label=meta["label"],
        reason="Действие выбрано по смыслу команды и доступным функциям MAX.",
        requires_confirmation=meta["mode"] == WRITE,
    )


def can_execute(plan: ActionPlan, approved: bool = False) -> bool:
    return plan.action in ACTIONS and (plan.mode == READ or approved)


def build_business_snapshot(products: Iterable[dict], leads: Iterable[dict], orders: Iterable[dict], plan: Iterable[dict]) -> Dict[str, Any]:
    products = list(products or [])
    leads = list(leads or [])
    orders = list(orders or [])
    content = list(plan or [])
    active_orders = [x for x in orders if str(x.get("status", "")) not in {"Завершён", "Отменён"}]
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
        "active_orders": len(active_orders),
        "content_items": len(content),
        "revenue": round(revenue, 2),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def audit_event(action: str, status: str, actor: str = "", details: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": str(action),
        "status": str(status),
        "actor": str(actor or "MAX"),
        "details": dict(details or {}),
    }
