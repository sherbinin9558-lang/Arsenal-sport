import streamlit as st

def apply_impeccable_theme():
    st.markdown("""
<style>
.stApp{background:#f5f6f8!important;color:#171a21!important}
.block-container{max-width:1440px!important;padding-top:1.4rem!important;padding-bottom:3rem!important}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6{color:#171a21!important;letter-spacing:-.025em!important}
.main-title{color:#171a21!important;font-size:.72rem!important;font-weight:800!important;letter-spacing:.16em!important;text-shadow:none!important}
.section-kicker{color:#5b5ce2!important;font-size:.68rem!important;font-weight:800!important;letter-spacing:.13em!important;text-shadow:none!important}
.section-title{color:#171a21!important;font-weight:800!important;letter-spacing:-.035em!important}
.section-subtitle{color:#68707f!important;font-size:.9rem!important;line-height:1.55!important}
section[data-testid="stSidebar"]{background:#11141b!important;border-right:1px solid #252a34!important}
section[data-testid="stSidebar"] .sidebar-brand-title{color:#f5f7fa!important;font-weight:800!important}
section[data-testid="stSidebar"] .sidebar-brand-kicker{color:#9299a8!important}
section[data-testid="stSidebar"] .sidebar-brand-version{color:#737b8b!important}
section[data-testid="stSidebar"] .sidebar-brand-line{background:#b8ff00!important;box-shadow:none!important}
.sidebar-max{background:#191d26!important;border:1px solid #2c323e!important;border-radius:14px!important;box-shadow:none!important}
.sidebar-max-kicker{color:#969eae!important}.sidebar-max-title{color:#fff!important}.sidebar-max-text{color:#8d95a5!important}
button[key="sidebar_max"]{background:#b8ff00!important;color:#101500!important;border:0!important;border-radius:11px!important;box-shadow:none!important;font-weight:800!important}
div[data-baseweb="tab-list"]{gap:3px!important;background:#fff!important;border:1px solid #e5e7eb!important;border-radius:13px!important;padding:4px!important;box-shadow:0 1px 2px rgba(17,24,39,.04),0 6px 20px rgba(17,24,39,.045)!important}
button[data-baseweb="tab"]{min-height:38px!important;border-radius:9px!important;background:transparent!important;border:0!important;color:#626a78!important;font-size:.82rem!important;font-weight:720!important}
button[data-baseweb="tab"][aria-selected="true"]{background:#efefff!important;color:#4748bf!important}
button[data-baseweb="tab"][aria-selected="true"] *{color:#4748bf!important}
.dashboard-hero{background:#fff!important;border:1px solid #e5e7eb!important;border-radius:18px!important;box-shadow:0 1px 2px rgba(17,24,39,.04),0 6px 20px rgba(17,24,39,.045)!important;padding:24px 26px!important}
.dashboard-hero-kicker{color:#5b5ce2!important;font-weight:800!important}
.dashboard-hero-title{color:#171a21!important;font-weight:820!important;letter-spacing:-.045em!important;text-shadow:none!important}
.dashboard-hero-text{color:#68707f!important}
.first-run-card,.max-ai-plan,.empty-state{background:#fff!important;border:1px solid #e5e7eb!important;border-radius:14px!important;box-shadow:0 1px 2px rgba(17,24,39,.04),0 6px 20px rgba(17,24,39,.045)!important}
[data-testid="stMetric"]{background:#fff!important;border:1px solid #e5e7eb!important;border-radius:14px!important;padding:14px 16px!important;box-shadow:0 1px 2px rgba(17,24,39,.04),0 6px 20px rgba(17,24,39,.045)!important}
[data-testid="stMetricLabel"]{color:#68707f!important;font-size:.72rem!important;font-weight:700!important}
[data-testid="stMetricValue"]{color:#171a21!important;font-size:1.42rem!important;font-weight:800!important}
.stApp input,.stApp textarea,.stApp [data-baseweb="select"]>div{border-color:#d5d9e1!important;border-radius:10px!important;background:#fff!important}
.stApp input:focus,.stApp textarea:focus{border-color:#5b5ce2!important;box-shadow:0 0 0 3px rgba(91,92,226,.1)!important}
.stApp input,.stApp textarea,.stApp [data-baseweb="select"] *{color:#171a21!important}
.stApp label{color:#454c59!important;font-size:.78rem!important;font-weight:680!important}
.stButton>button,.stDownloadButton>button{min-height:40px!important;border-radius:10px!important;border:1px solid #d5d9e1!important;background:#fff!important;color:#303641!important;font-weight:720!important;box-shadow:none!important}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#aeb5c3!important;box-shadow:0 5px 14px rgba(17,24,39,.06)!important}
.stButton>button[kind="primary"],button[kind="primary"]{background:#5b5ce2!important;color:#fff!important;border-color:#5b5ce2!important;box-shadow:0 6px 16px rgba(91,92,226,.18)!important}
[data-testid="stAlert"],[data-testid="stExpander"]{border-radius:12px!important;border:1px solid #e5e7eb!important;box-shadow:none!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid #e5e7eb!important;border-radius:14px!important;overflow:hidden!important}
@media(max-width:768px){.block-container{padding:.7rem .7rem 2rem!important}div[data-baseweb="tab-list"]{overflow-x:auto!important;flex-wrap:nowrap!important;scrollbar-width:none!important}button[data-baseweb="tab"]{flex:0 0 auto!important;white-space:nowrap!important;font-size:.75rem!important;padding:8px 10px!important}[data-testid="stHorizontalBlock"]{flex-direction:column!important;gap:.55rem!important}[data-testid="stHorizontalBlock"]>[data-testid="column"]{width:100%!important;min-width:100%!important;max-width:100%!important}.dashboard-hero{padding:19px 17px!important}.stButton>button,.stDownloadButton>button{min-height:44px!important}}
</style>
""", unsafe_allow_html=True)

    if st.session_state.get("theme_toggle", False):
        st.markdown("""<style>
.stApp{background:#0b0e13!important;color:#f5f7fa!important}.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6{color:#f5f7fa!important}.section-title,.main-title{color:#f5f7fa!important}.section-subtitle,.dashboard-hero-text{color:#9aa3b2!important}.dashboard-hero,.first-run-card,.max-ai-plan,.empty-state,[data-testid="stMetric"],[data-testid="stExpander"],[data-testid="stDataFrame"],[data-testid="stTable"]{background:#11151d!important;border-color:#252b38!important;color:#f5f7fa!important}.dashboard-hero-title,[data-testid="stMetricValue"]{color:#f5f7fa!important}.stApp input,.stApp textarea,.stApp [data-baseweb="select"]>div{background:#11151d!important;border-color:#394152!important;color:#f5f7fa!important}.stApp label,[data-testid="stMetricLabel"]{color:#9aa3b2!important}.stButton>button,.stDownloadButton>button{background:#11151d!important;border-color:#394152!important;color:#f5f7fa!important}div[data-baseweb="tab-list"]{background:#11151d!important;border-color:#252b38!important}button[data-baseweb="tab"][aria-selected="true"]{background:#272650!important;color:#c9c7ff!important}
</style>""", unsafe_allow_html=True)
