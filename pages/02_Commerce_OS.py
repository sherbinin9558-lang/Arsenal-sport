"""Legacy page guard.

These pages are retired from the production SaaS surface.
All production data must go through the tenant-aware application in app.py.
Do not reintroduce direct JSON access here.
"""

import streamlit as st

st.set_page_config(page_title="AI Agent Content Manager", page_icon="⚡", layout="wide")

st.error("Этот раздел больше не используется в production-версии.")
st.caption("Professional Core и Commerce OS перенесены в основное SaaS-приложение с tenant isolation.")

if st.button("← Вернуться в приложение", type="primary", use_container_width=True):
    st.switch_page("app.py")

st.stop()
