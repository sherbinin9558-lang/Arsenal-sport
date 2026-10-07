"""Commercial AI usage metering.

The current MAX/growth engine is deterministic and free-first, so its recorded
provider cost is normally zero. The same event model also supports future paid
LLM calls by passing input/output tokens and configured RUB-per-1K prices.
Failures in metering never break the merchant workflow.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st


def _cfg(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, os.getenv(name, default))
    except Exception:
        value = os.getenv(name, default)
    return str(value or "").strip()


def estimate_cost_rub(input_tokens: int = 0, output_tokens: int = 0) -> float:
    """Estimate cost from optional per-1K-token RUB prices."""
    try:
        in_rate = float(_cfg("AI_INPUT_RUB_PER_1K", "0").replace(",", "."))
        out_rate = float(_cfg("AI_OUTPUT_RUB_PER_1K", "0").replace(",", "."))
    except (TypeError, ValueError):
        in_rate = out_rate = 0.0
    cost = (max(0, int(input_tokens)) / 1000.0) * in_rate
    cost += (max(0, int(output_tokens)) / 1000.0) * out_rate
    return round(cost, 6)


def record_ai_usage(
    operation: str,
    *,
    provider: str = "local",
    model: str = "deterministic",
    input_tokens: int = 0,
    output_tokens: int = 0,
    request_count: int = 1,
    estimated_cost_rub: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Persist a tenant/user-scoped AI usage event when SaaS is enabled."""
    cost = estimate_cost_rub(input_tokens, output_tokens) if estimated_cost_rub is None else max(0.0, float(estimated_cost_rub))
    payload = {
        "tenant_id": str(st.session_state.get("saas_tenant_id") or ""),
        "user_id": str(st.session_state.get("saas_user_id") or ""),
        "operation": str(operation)[:120],
        "provider": str(provider)[:60],
        "model": str(model)[:120],
        "input_tokens": max(0, int(input_tokens)),
        "output_tokens": max(0, int(output_tokens)),
        "request_count": max(1, int(request_count)),
        "estimated_cost_rub": cost,
        "metadata": dict(metadata or {}),
    }
    if not payload["tenant_id"] or not payload["user_id"]:
        return False

    try:
        from saas_core import _rest_post, saas_enabled
        if not saas_enabled():
            st.session_state["_ai_usage_events"] = st.session_state.get("_ai_usage_events", [])[-99:] + [payload]
            return True
        token = st.session_state.get("saas_access_token")
        if not token:
            return False
        _rest_post("/rest/v1/ai_usage_events", token, payload)
        return True
    except Exception:
        # Metering is observability, not a dependency of the business action.
        return False


def usage_summary(days: int = 30) -> dict[str, Any]:
    """Return tenant-scoped usage totals for the current authenticated user."""
    days = max(1, min(int(days), 365))
    try:
        from saas_core import _rest_get, saas_enabled
        if not saas_enabled():
            rows = st.session_state.get("_ai_usage_events", [])
        else:
            token = st.session_state.get("saas_access_token")
            tenant_id = str(st.session_state.get("saas_tenant_id") or "")
            if not token or not tenant_id:
                return {"events": 0, "requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_rub": 0.0, "by_operation": {}}
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            rows = _rest_get(
                "/rest/v1/ai_usage_events",
                token,
                params={
                    "select": "operation,request_count,input_tokens,output_tokens,estimated_cost_rub,created_at",
                    "tenant_id": f"eq.{tenant_id}",
                    "created_at": f"gte.{since}",
                    "order": "created_at.desc",
                    "limit": "5000",
                },
            )
    except Exception:
        rows = []

    by_operation: dict[str, dict[str, float]] = defaultdict(lambda: {"requests": 0, "cost_rub": 0.0})
    events = 0
    requests = 0
    input_tokens = 0
    output_tokens = 0
    cost = 0.0
    for row in rows or []:
        events += 1
        requests += int(row.get("request_count", 0) or 0)
        input_tokens += int(row.get("input_tokens", 0) or 0)
        output_tokens += int(row.get("output_tokens", 0) or 0)
        cost += float(row.get("estimated_cost_rub", 0) or 0)
        op = str(row.get("operation") or "unknown")
        by_operation[op]["requests"] += int(row.get("request_count", 0) or 0)
        by_operation[op]["cost_rub"] += float(row.get("estimated_cost_rub", 0) or 0)

    return {
        "events": events,
        "requests": requests,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_rub": round(cost, 6),
        "by_operation": dict(by_operation),
    }
