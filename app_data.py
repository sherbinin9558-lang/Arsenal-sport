import io
from pathlib import Path

import streamlit as st
from PIL import Image

from growth_engine import ai_summary
from saas_core import (
    data_count,
    data_delete_record,
    data_load,
    data_save,
    data_update_record,
    feature_allowed,
    saas_enabled,
    tenant_plan,
)
from asset_store import load_logo_bytes, save_logo_bytes


ATTRIBUTION_FILE = Path("content_attribution.json")


def max_product_title(product):
    """Return a safe short product title for dashboard/MAX summaries."""
    if not isinstance(product, dict):
        return "Товар"
    return str(product.get("name") or product.get("title") or "Товар").strip() or "Товар"


def load_products():
    key = "_app_products_cache"
    if key not in st.session_state:
        st.session_state[key] = data_load("products", [])
    return st.session_state[key]


def save_products(p):
    data_save("products", p)
    st.session_state["_app_products_cache"] = p
    st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
    st.session_state.pop("max_data_snapshot", None)


def add_product(prod):
    p = load_products()
    if not feature_allowed("products", len(p)):
        raise ValueError(f"Лимит каталога тарифа {tenant_plan().upper()} достигнут.")
    p.append(prod)
    save_products(p)


def _find_record_index(rows, record_id):
    if isinstance(record_id, int):
        return record_id if 0 <= record_id < len(rows) else None
    target = str(record_id or "").strip()
    if not target:
        return None
    for idx, row in enumerate(rows):
        if str(row.get("_saas_record_id", "")) == target:
            return idx
    return None


def update_product(record_id, prod, existing=None):
    if existing is not None and existing.get("_saas_record_id") and existing.get("_saas_updated_at") and saas_enabled():
        merged = dict(existing)
        merged.update(dict(prod or {}))
        merged.pop("_saas_updated_at", None)
        data_update_record("products", existing["_saas_record_id"], merged, existing["_saas_updated_at"])
        st.session_state.pop("_app_products_cache", None)
        st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
        st.session_state.pop("max_data_snapshot", None)
        return
    p = load_products()
    idx = _find_record_index(p, record_id)
    if idx is not None:
        current = dict(p[idx] or {})
        updated = dict(prod or {})
        stable_id = current.get("_saas_record_id")
        current.update(updated)
        if stable_id:
            current["_saas_record_id"] = stable_id
        else:
            current.pop("_saas_record_id", None)
        p[idx] = current
        save_products(p)


def delete_product(record_id, existing=None):
    if existing is not None and existing.get("_saas_record_id") and existing.get("_saas_updated_at") and saas_enabled():
        data_delete_record("products", existing["_saas_record_id"], existing["_saas_updated_at"])
        st.session_state.pop("_app_products_cache", None)
        st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
        st.session_state.pop("max_data_snapshot", None)
        return
    p = load_products()
    idx = _find_record_index(p, record_id)
    if idx is not None:
        p.pop(idx)
        save_products(p)


def _growth_snapshot(products, plan, leads, orders):
    """Reuse expensive growth analytics across ordinary Streamlit reruns."""
    key = (
        id(products), id(plan), id(leads), id(orders),
        len(products), len(plan), len(leads), len(orders),
    )
    if st.session_state.get("_app_growth_snapshot_key") != key:
        st.session_state["_app_growth_snapshot"] = ai_summary(products, leads, orders, plan)
        st.session_state["_app_growth_snapshot_key"] = key
    return st.session_state["_app_growth_snapshot"]


def _cached_growth_recommendations(products, leads, orders, plan):
    return _growth_snapshot(products, plan, leads, orders).get("recommendations", [])


def load_plan():
    key = "_app_plan_cache"
    if key not in st.session_state:
        st.session_state[key] = data_load("content_plan", [])
    return st.session_state[key]


def save_plan(pl):
    data_save("content_plan", pl)
    st.session_state["_app_plan_cache"] = pl
    st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
    st.session_state.pop("max_data_snapshot", None)


def load_attribution():
    return data_load("content_attribution", [])


def save_attribution(items):
    data_save("content_attribution", items)


def attribution_metrics(attribution, leads, orders):
    by_product = {}
    for item in attribution:
        key = str(item.get("product_id") or item.get("product") or "")
        if not key:
            continue
        row = by_product.setdefault(key, {"content": 0, "leads": 0, "orders": 0})
        row["content"] += 1
        row["leads"] += int(item.get("leads", 0) or 0)
        row["orders"] += int(item.get("orders", 0) or 0)
    return by_product


def add_plan(item):
    p = load_plan()
    if not feature_allowed("content", len(p)):
        raise ValueError(f"Лимит контента тарифа {tenant_plan().upper()} достигнут.")
    p.append(item)
    save_plan(p)


def update_plan(record_id, item):
    p = load_plan()
    idx = _find_record_index(p, record_id)
    if idx is None:
        return
    existing = dict(p[idx] or {})
    updated = dict(item or {})
    stable_id = existing.get("_saas_record_id")
    expected = existing.get("_saas_updated_at")
    if stable_id and expected and saas_enabled():
        merged = dict(existing)
        merged.update(updated)
        merged.pop("_saas_updated_at", None)
        data_update_record("content_plan", stable_id, merged, expected)
        st.session_state.pop("_app_plan_cache", None)
        st.session_state.pop("max_data_snapshot", None)
        st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
        return
    if stable_id:
        existing["_saas_record_id"] = stable_id
    else:
        existing.pop("_saas_record_id", None)
    existing.update(updated)
    p[idx] = existing
    save_plan(p)


def delete_plan(record_id):
    p = load_plan()
    idx = _find_record_index(p, record_id)
    if idx is None:
        return
    existing = dict(p[idx] or {})
    stable_id = existing.get("_saas_record_id")
    expected = existing.get("_saas_updated_at")
    if stable_id and expected and saas_enabled():
        data_delete_record("content_plan", stable_id, expected)
        st.session_state.pop("_app_plan_cache", None)
        st.session_state.pop("max_data_snapshot", None)
        st.session_state["_app_data_revision"] = st.session_state.get("_app_data_revision", 0) + 1
        return
    p.pop(idx)
    save_plan(p)


def _tenant_asset_root():
    root = Path("tenant_assets") / str(st.session_state.get("saas_tenant_id", "unknown"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_logo():
    data = load_logo_bytes()
    if not data:
        return None
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def save_logo(f):
    img = Image.open(f).convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    save_logo_bytes(buf.getvalue())
