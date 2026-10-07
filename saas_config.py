"""Small, dependency-light SaaS configuration helpers.

Kept separate from the data/auth implementation so configuration changes do not
require editing the large SaaS core module.
"""

import os
import streamlit as st


PLAN_LIMITS = {
    "trial": {"products": 100, "users": 1, "content": 100},
    "starter": {"products": 7000, "users": 3, "content": 1000},
    "pro": {"products": 7000, "users": 10, "content": 10000},
    "business": {"products": 100000, "users": 50, "content": 100000},
}


def cfg(name, default=""):
    try:
        value = st.secrets.get(name, os.getenv(name, default))
    except Exception:
        value = os.getenv(name, default)
    return str(value or "").strip()


def supabase_config():
    return cfg("SUPABASE_URL").rstrip("/"), cfg("SUPABASE_ANON_KEY")


def saas_enabled():
    url, key = supabase_config()
    return bool(url and key)


def demo_mode_enabled():
    return cfg("DEMO_MODE", "false").lower() in ("1", "true", "yes", "on")


def public_app_url():
    return cfg(
        "SAAS_PUBLIC_URL",
        "https://arsenal-sport-b3rvpnysmxhvw9wud8wjjd.streamlit.app",
    ).rstrip("/")
