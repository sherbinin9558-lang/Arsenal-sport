"""Platform owner console helpers kept separate from the SaaS runtime core."""

import requests
import streamlit as st

from saas_config import cfg as _cfg, supabase_config


def _service_key():
    return _cfg("SUPABASE_SERVICE_ROLE_KEY")


def platform_admin_enabled():
    email = _cfg("SAAS_ADMIN_EMAIL").lower()
    return bool(email and st.session_state.get("saas_email", "").lower() == email)


def _admin_headers():
    key = _service_key()
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY не настроен.")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _admin_request(method, path, **kwargs):
    url, _ = supabase_config()
    if not url:
        raise RuntimeError("SUPABASE_URL не настроен.")
    headers = _admin_headers()
    r = requests.request(method, f"{url}{path}", headers=headers, timeout=20, **kwargs)
    try:
        data = r.json()
    except Exception:
        data = {"message": r.text}
    if not r.ok:
        raise RuntimeError(
            data.get("message") or data.get("error") or data.get("msg") or str(data)
        )
    return data


def platform_admin_snapshot():
    if not platform_admin_enabled():
        raise PermissionError("Доступ к Owner Console запрещён.")
    tenants = _admin_request(
        "GET",
        "/rest/v1/tenants",
        params={"select": "id,name,slug,plan,status,created_at", "order": "created_at.desc"},
    )
    subs = _admin_request(
        "GET",
        "/rest/v1/subscriptions",
        params={"select": "tenant_id,plan,status,provider,current_period_end,auto_renew", "order": "tenant_id"},
    )
    members = _admin_request(
        "GET",
        "/rest/v1/memberships",
        params={"select": "tenant_id,user_id,role,created_at", "order": "created_at.asc"},
    )
    try:
        users = _admin_request(
            "GET",
            "/auth/v1/admin/users",
            params={"page": 1, "per_page": 1000},
        ).get("users", [])
    except Exception:
        users = []
    return tenants, subs, members, users


def platform_admin_set_tenant(tenant_id_value, plan=None, status=None):
    if not platform_admin_enabled():
        raise PermissionError("Доступ к Owner Console запрещён.")
    payload = {}
    if plan is not None:
        payload["plan"] = plan
    if status is not None:
        payload["status"] = status
    if not payload:
        return
    _admin_request(
        "PATCH",
        "/rest/v1/tenants",
        params={"id": f"eq.{tenant_id_value}"},
        json=payload,
    )


def platform_admin_set_subscription(
    tenant_id_value, plan=None, status=None, auto_renew=None
):
    if not platform_admin_enabled():
        raise PermissionError("Доступ к Owner Console запрещён.")
    payload = {}
    if plan is not None:
        payload["plan"] = plan
    if status is not None:
        payload["status"] = status
    if auto_renew is not None:
        payload["auto_renew"] = bool(auto_renew)
    if not payload:
        return
    _admin_request(
        "PATCH",
        "/rest/v1/subscriptions",
        params={"tenant_id": f"eq.{tenant_id_value}"},
        json=payload,
    )
