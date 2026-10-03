"""Tenant file storage: Supabase Storage with a local-disk fallback.

Files live in the private ``tenant-assets`` bucket under ``<tenant_id>/<name>``.
Access goes through the signed-in user's token, so the database policies in
supabase_schema.sql decide who can read or write. Nothing here uses the
service-role key. If Supabase is not configured, the user is not signed in, or
a request fails, the previous local-disk behaviour is used instead.
"""
import logging
import re
from pathlib import Path

BUCKET = "tenant-assets"
LOGO_NAME = "logo.png"
LOCAL_ROOT = Path("tenant_assets")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")

log = logging.getLogger(__name__)


def is_tenant_uuid(value):
    return bool(_UUID_RE.match(str(value or "")))


def _object_url(base_url, tenant_id, name, authenticated=False):
    if not is_tenant_uuid(tenant_id) or not _NAME_RE.match(str(name or "")):
        raise ValueError("Invalid tenant id or file name")
    prefix = "authenticated/" if authenticated else ""
    return f"{str(base_url).rstrip('/')}/storage/v1/object/{prefix}{BUCKET}/{tenant_id}/{name}"


def _headers(anon_key, token, extra=None):
    headers = {"apikey": anon_key, "Authorization": f"Bearer {token}"}
    headers.update(extra or {})
    return headers


def _http(http):
    if http is not None:
        return http
    import requests
    return requests


def storage_put(base_url, anon_key, token, tenant_id, name, data, content_type, http=None):
    """Upload (or replace) one file. Returns True on success, never raises."""
    try:
        url = _object_url(base_url, tenant_id, name)
        response = _http(http).post(
            url,
            data=data,
            headers=_headers(anon_key, token, {"Content-Type": content_type, "x-upsert": "true"}),
            timeout=20,
        )
        if response.status_code in (200, 201):
            return True
        log.warning("Storage upload failed (%s) for %s", response.status_code, name)
    except Exception as exc:
        log.warning("Storage upload error for %s: %s", name, exc)
    return False


def storage_get(base_url, anon_key, token, tenant_id, name, http=None):
    """Download one file. Returns bytes, or None if missing or on any error."""
    try:
        url = _object_url(base_url, tenant_id, name, authenticated=True)
        response = _http(http).get(url, headers=_headers(anon_key, token), timeout=20)
        if response.status_code == 200:
            return response.content
        if response.status_code not in (400, 404):
            log.warning("Storage download failed (%s) for %s", response.status_code, name)
    except Exception as exc:
        log.warning("Storage download error for %s: %s", name, exc)
    return None


# ---------------------------------------------------------------- logo helpers
def _session():
    import streamlit as st
    from saas_core import _supabase_config

    url, anon_key = _supabase_config()
    return (
        st,
        url,
        anon_key,
        st.session_state.get("saas_access_token"),
        st.session_state.get("saas_tenant_id", "unknown"),
    )


def _local_logo_path(tenant):
    return LOCAL_ROOT / str(tenant) / LOGO_NAME


def save_logo_bytes(png_bytes):
    """Save the tenant logo: local copy always, Supabase Storage when possible."""
    st, url, anon_key, token, tenant = _session()
    path = _local_logo_path(tenant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)
    if url and anon_key and token and is_tenant_uuid(tenant):
        storage_put(url, anon_key, token, tenant, LOGO_NAME, png_bytes, "image/png")
    st.session_state[f"_logo_bytes_{tenant}"] = png_bytes


def load_logo_bytes():
    """Return the tenant logo as PNG bytes, or None if there is none."""
    st, url, anon_key, token, tenant = _session()
    cache_key = f"_logo_bytes_{tenant}"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]

    data = None
    if url and anon_key and token and is_tenant_uuid(tenant):
        data = storage_get(url, anon_key, token, tenant, LOGO_NAME)
    path = _local_logo_path(tenant)
    if data is None and path.exists():
        try:
            data = path.read_bytes()
        except Exception:
            data = None
    if data:
        st.session_state[cache_key] = data
    return data
