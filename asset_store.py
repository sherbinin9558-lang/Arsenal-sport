"""Tenant file storage backed by private Supabase Storage.

Production assets are stored only in the private ``tenant-assets`` bucket under
``<tenant_id>/<name>`. Access goes through the signed-in user's JWT, so the
Storage RLS policies in ``supabase_schema.sql`` decide who can read or write.
Nothing here uses the service-role key.

A local-disk fallback is allowed only when DEMO_MODE=true. Production must never
report a successful asset save unless Supabase Storage accepted the object.
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


class AssetStoreError(RuntimeError):
    """Raised when a production asset cannot be persisted to Supabase Storage."""


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
    """Upload (or replace) one file. Returns True only when Storage confirms success."""
    try:
        url = _object_url(base_url, tenant_id, name)
        response = _http(http).post(
            url,
            data=data,
            headers=_headers(
                anon_key,
                token,
                {"Content-Type": content_type, "x-upsert": "true"},
            ),
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


# ---------------------------------------------------------------- session/storage helpers
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


def _storage_context():
    """Return the authenticated production Storage context or raise a clear error."""
    st, url, anon_key, token, tenant = _session()
    if not url or not anon_key:
        raise AssetStoreError(
            "Supabase Storage не настроен. Для production-ассетов требуется SUPABASE_URL и SUPABASE_ANON_KEY."
        )
    if not token:
        raise AssetStoreError("Нет активной Supabase-сессии для сохранения production-ассета.")
    if not is_tenant_uuid(tenant):
        raise AssetStoreError("Некорректный tenant_id для сохранения production-ассета.")
    return st, url, anon_key, token, tenant


def _demo_mode():
    from saas_core import demo_mode_enabled
    return demo_mode_enabled()


def _local_logo_path(tenant):
    return LOCAL_ROOT / str(tenant) / LOGO_NAME


def save_asset_bytes(name, data, content_type, *, local_path=None):
    """Persist an asset. Production writes only to Supabase Storage.

    When DEMO_MODE=true, a local path may be used for an intentionally local demo.
    The function returns a stable storage reference or local path.
    """
    try:
        st, url, anon_key, token, tenant = _storage_context()
    except AssetStoreError:
        if not _demo_mode():
            raise
        if local_path is None:
            local_path = LOCAL_ROOT / "demo" / str(name)
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    if not storage_put(url, anon_key, token, tenant, name, data, content_type):
        raise AssetStoreError(
            f"Не удалось сохранить production-ассет в Supabase Storage: {name}"
        )
    return f"storage://{BUCKET}/{tenant}/{name}"


def load_asset_bytes(name, *, local_path=None):
    """Load an asset from Storage in production; local files are demo-only."""
    try:
        st, url, anon_key, token, tenant = _storage_context()
    except AssetStoreError:
        if not _demo_mode():
            raise
        if local_path is None:
            local_path = LOCAL_ROOT / "demo" / str(name)
        path = Path(local_path)
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except Exception as exc:
            log.warning("Demo asset read failed for %s: %s", name, exc)
            return None

    return storage_get(url, anon_key, token, tenant, name)


# ---------------------------------------------------------------- logo helpers
def save_logo_bytes(png_bytes):
    """Save the tenant logo to Supabase Storage in production."""
    st, url, anon_key, token, tenant = _session()
    cache_key = f"_logo_bytes_{tenant}"
    local_path = _local_logo_path(tenant)
    reference = save_asset_bytes(
        LOGO_NAME,
        png_bytes,
        "image/png",
        local_path=local_path,
    )
    st.session_state[cache_key] = png_bytes
    return reference


def load_logo_bytes():
    """Return the tenant logo from Storage in production, or None if absent."""
    st, url, anon_key, token, tenant = _session()
    cache_key = f"_logo_bytes_{tenant}"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]

    data = load_asset_bytes(LOGO_NAME, local_path=_local_logo_path(tenant))
    if data:
        st.session_state[cache_key] = data
    return data
