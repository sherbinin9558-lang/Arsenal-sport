"""Billing/account helpers extracted from saas_core.py."""

import os
import requests
import streamlit as st


def plan_catalog():
    return {
        "starter": {"name": "STARTER", "products": 7000, "users": 3, "description": "Для небольшого магазина"},
        "pro": {"name": "PRO", "products": 7000, "users": 10, "description": "Для растущего бизнеса"},
        "business": {"name": "BUSINESS", "products": 100000, "users": 50, "description": "Для сети и большого каталога"},
    }


def activate_paid_subscription(
    plan,
    provider_payment_id,
    payment_method_id=None,
    provider="yookassa",
    tenant=None,
    *,
    service_key,
    supabase_url,
    saas_is_enabled,
    tenant_id,
):
    if not service_key or not saas_is_enabled:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY не настроен.")
    if plan not in ("starter", "pro", "business"):
        raise ValueError("Недопустимый тариф.")
    if not provider_payment_id:
        raise ValueError("provider_payment_id обязателен.")
    tid = str(tenant or tenant_id())
    base = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    response = requests.post(
        f"{base}/rpc/activate_paid_subscription",
        headers=headers,
        json={
            "p_tenant_id": tid,
            "p_plan": plan,
            "p_provider": str(provider),
            "p_provider_payment_id": str(provider_payment_id),
            "p_provider_payment_method_id": str(payment_method_id) if payment_method_id else None,
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError("Не удалось обновить состояние подписки. Проверьте настройки и журнал сервиса.")
    st.session_state["saas_plan"] = plan
    st.session_state["saas_tenant_status"] = "active"
    return True


def set_auto_renew(
    enabled,
    *,
    tenant_id,
    saas_is_enabled,
    current_role,
    service_key,
    supabase_url,
):
    tid = tenant_id()
    if not saas_is_enabled:
        st.session_state["auto_renew"] = bool(enabled)
        return True
    if current_role() not in ("owner", "admin"):
        raise PermissionError("Только владелец или администратор может менять автопродление.")
    if not service_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY не настроен.")
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    response = requests.patch(
        f"{supabase_url}/rest/v1/subscriptions",
        headers=headers,
        params={"tenant_id": f"eq.{tid}"},
        json={"auto_renew": bool(enabled), "cancel_at_period_end": not bool(enabled)},
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError("Не удалось обновить настройки автопродления. Проверьте журнал сервиса.")
    st.session_state["auto_renew"] = bool(enabled)
    return True


def subscription_snapshot(
    *,
    token,
    tenant_id,
    saas_is_enabled,
    subscription_loader,
    tenant_plan,
):
    tid = tenant_id()
    if not saas_is_enabled or not token:
        return {
            "plan": tenant_plan(),
            "status": "trialing",
            "provider": None,
            "current_period_end": None,
            "auto_renew": False,
            "cancel_at_period_end": False,
            "next_billing_at": None,
        }
    try:
        row = subscription_loader(token, tid) or {}
        return {
            "plan": row.get("plan", tenant_plan()),
            "status": row.get("status", "trialing"),
            "provider": row.get("provider"),
            "current_period_end": row.get("current_period_end"),
            "auto_renew": bool(row.get("auto_renew", False)),
            "cancel_at_period_end": bool(row.get("cancel_at_period_end", False)),
            "next_billing_at": row.get("next_billing_at"),
        }
    except Exception:
        return {
            "plan": tenant_plan(),
            "status": "unknown",
            "provider": None,
            "current_period_end": None,
            "auto_renew": False,
            "cancel_at_period_end": False,
            "next_billing_at": None,
        }


def request_plan_change(plan, *, state):
    if plan not in ("starter", "pro", "business"):
        raise ValueError("Недопустимый тариф.")
    state["requested_plan"] = plan
    return True
