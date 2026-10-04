import streamlit as st

def apply_impeccable_theme():
    """Presentation-only design system for the whole Arsenal Sport panel.

    This function intentionally changes CSS only. It does not touch data,
    authentication, business logic, WebMCP, API calls, or widget state.
    """
    st.markdown(
        """
<style>
:root{
  --as-bg:#f4f5f7;
  --as-surface:#ffffff;
  --as-surface-soft:#f8f9fb;
  --as-border:#e4e7ec;
  --as-border-strong:#d6dae2;
  --as-text:#171a21;
  --as-muted:#6b7280;
  --as-muted-2:#8a92a1;
  --as-primary:#5b5ce2;
  --as-primary-soft:#eeeeff;
  --as-primary-strong:#494ac7;
  --as-green:#b8ff00;
  --as-dark:#11141b;
  --as-dark-2:#191d26;
  --as-dark-border:#2a303b;
  --as-radius:16px;
  --as-shadow:0 1px 2px rgba(16,24,40,.04),0 8px 24px rgba(16,24,40,.045);
}

.stApp{
  background:var(--as-bg)!important;
  color:var(--as-text)!important;
}
.block-container{
  max-width:1480px!important;
  padding-top:1.15rem!important;
  padding-bottom:3.2rem!important;
}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6{
  color:var(--as-text)!important;
  letter-spacing:-.028em!important;
}
.stApp p,.stApp li{
  color:var(--as-text);
}
.main-title{
  color:var(--as-text)!important;
  font-size:.70rem!important;
  line-height:1!important;
  font-weight:850!important;
  letter-spacing:.18em!important;
  margin:0 0 .45rem!important;
  text-shadow:none!important;
}
.mobile-nav-hint{
  color:var(--as-muted-2)!important;
  font-size:.72rem!important;
  margin-bottom:.6rem!important;
}
.section-kicker{
  color:var(--as-primary)!important;
  font-size:.67rem!important;
  line-height:1.2!important;
  font-weight:850!important;
  letter-spacing:.14em!important;
  text-transform:uppercase!important;
  text-shadow:none!important;
}
.section-title{
  color:var(--as-text)!important;
  font-size:clamp(1.55rem,2.3vw,2.25rem)!important;
  line-height:1.08!important;
  font-weight:850!important;
  letter-spacing:-.045em!important;
  margin-top:.2rem!important;
}
.section-subtitle{
  color:var(--as-muted)!important;
  font-size:.91rem!important;
  line-height:1.55!important;
  max-width:820px!important;
}

/* Sidebar */
section[data-testid="stSidebar"]{
  background:var(--as-dark)!important;
  border-right:1px solid #202530!important;
}
section[data-testid="stSidebar"] > div{
  background:var(--as-dark)!important;
}
section[data-testid="stSidebar"] .sidebar-brand-title{
  color:#f6f7f9!important;
  font-weight:850!important;
  letter-spacing:-.02em!important;
}
section[data-testid="stSidebar"] .sidebar-brand-kicker{
  color:#9aa2b1!important;
  font-size:.68rem!important;
  font-weight:750!important;
  letter-spacing:.12em!important;
}
section[data-testid="stSidebar"] .sidebar-brand-version{
  color:#70798a!important;
  font-size:.63rem!important;
  letter-spacing:.08em!important;
}
section[data-testid="stSidebar"] .sidebar-brand-line{
  height:3px!important;
  width:42px!important;
  background:var(--as-green)!important;
  border-radius:99px!important;
  box-shadow:none!important;
}
section[data-testid="stSidebar"] hr{
  border-color:var(--as-dark-border)!important;
}
.sidebar-max{
  background:var(--as-dark-2)!important;
  border:1px solid var(--as-dark-border)!important;
  border-radius:14px!important;
  box-shadow:none!important;
  padding:14px!important;
}
.sidebar-max-kicker{
  color:#949dac!important;
  font-size:.62rem!important;
  letter-spacing:.08em!important;
}
.sidebar-max-title{
  color:#fff!important;
  font-size:1.05rem!important;
  font-weight:850!important;
}
.sidebar-max-text{
  color:#8d95a5!important;
  font-size:.78rem!important;
}
button[key="sidebar_max"]{
  background:var(--as-green)!important;
  color:#101500!important;
  border:0!important;
  border-radius:11px!important;
  box-shadow:none!important;
  font-weight:850!important;
}
button[key="sidebar_max"]:hover{
  background:#c8ff3a!important;
  box-shadow:0 5px 16px rgba(184,255,0,.14)!important;
}

/* Main navigation */
div[data-baseweb="tab-list"]{
  display:flex!important;
  gap:3px!important;
  background:var(--as-surface)!important;
  border:1px solid var(--as-border)!important;
  border-radius:14px!important;
  padding:4px!important;
  margin:.35rem 0 1.15rem!important;
  box-shadow:0 1px 2px rgba(16,24,40,.035),0 6px 20px rgba(16,24,40,.04)!important;
}
button[data-baseweb="tab"]{
  min-height:39px!important;
  border-radius:10px!important;
  background:transparent!important;
  border:0!important;
  color:#626a78!important;
  font-size:.80rem!important;
  font-weight:760!important;
  padding:7px 12px!important;
  white-space:nowrap!important;
}
button[data-baseweb="tab"]:hover{
  color:var(--as-text)!important;
  background:#f7f7fa!important;
}
button[data-baseweb="tab"][aria-selected="true"]{
  background:var(--as-primary-soft)!important;
  color:#4748bf!important;
  box-shadow:none!important;
}
button[data-baseweb="tab"][aria-selected="true"] *{
  color:#4748bf!important;
}

/* Hero / cards */
.dashboard-hero,
.first-run-card,
.max-ai-plan,
.empty-state{
  background:var(--as-surface)!important;
  border:1px solid var(--as-border)!important;
  border-radius:18px!important;
  box-shadow:var(--as-shadow)!important;
}
.dashboard-hero{
  padding:25px 27px!important;
  margin-bottom:1rem!important;
}
.dashboard-hero-kicker{
  color:var(--as-primary)!important;
  font-size:.67rem!important;
  font-weight:850!important;
  letter-spacing:.13em!important;
}
.dashboard-hero-title{
  color:var(--as-text)!important;
  font-size:clamp(1.55rem,3vw,2.45rem)!important;
  line-height:1.05!important;
  font-weight:850!important;
  letter-spacing:-.05em!important;
  text-shadow:none!important;
}
.dashboard-hero-text{
  color:var(--as-muted)!important;
  font-size:.92rem!important;
  line-height:1.55!important;
  max-width:820px!important;
}

/* Metrics */
[data-testid="stMetric"]{
  background:var(--as-surface)!important;
  border:1px solid var(--as-border)!important;
  border-radius:15px!important;
  padding:15px 17px!important;
  min-height:94px!important;
  box-shadow:var(--as-shadow)!important;
}
[data-testid="stMetricLabel"]{
  color:var(--as-muted)!important;
  font-size:.70rem!important;
  font-weight:750!important;
  letter-spacing:.01em!important;
}
[data-testid="stMetricValue"]{
  color:var(--as-text)!important;
  font-size:1.40rem!important;
  font-weight:850!important;
  letter-spacing:-.025em!important;
}
[data-testid="stMetricDelta"]{
  font-size:.72rem!important;
}

/* Inputs / selectors */
.stApp input,
.stApp textarea,
.stApp [data-baseweb="select"]>div{
  border-color:var(--as-border-strong)!important;
  border-radius:11px!important;
  background:var(--as-surface)!important;
  min-height:40px;
}
.stApp input:focus,
.stApp textarea:focus{
  border-color:var(--as-primary)!important;
  box-shadow:0 0 0 3px rgba(91,92,226,.10)!important;
}
.stApp input,
.stApp textarea,
.stApp [data-baseweb="select"] *{
  color:var(--as-text)!important;
}
.stApp input::placeholder,
.stApp textarea::placeholder{
  color:#9aa1ad!important;
}
.stApp label{
  color:#454c59!important;
  font-size:.77rem!important;
  font-weight:700!important;
}

/* Buttons */
.stButton>button,
.stDownloadButton>button,
.stFormSubmitButton>button{
  min-height:40px!important;
  border-radius:11px!important;
  border:1px solid var(--as-border-strong)!important;
  background:var(--as-surface)!important;
  color:#303641!important;
  font-weight:760!important;
  box-shadow:none!important;
  transition:transform .12s ease,box-shadow .12s ease,border-color .12s ease!important;
}
.stButton>button:hover,
.stDownloadButton>button:hover,
.stFormSubmitButton>button:hover{
  border-color:#aeb5c3!important;
  box-shadow:0 6px 16px rgba(16,24,40,.07)!important;
  transform:translateY(-1px);
}
.stButton>button[kind="primary"],
.stFormSubmitButton>button[kind="primary"],
button[kind="primary"]{
  background:var(--as-primary)!important;
  color:#fff!important;
  border-color:var(--as-primary)!important;
  box-shadow:0 7px 18px rgba(91,92,226,.18)!important;
}
.stButton>button[kind="primary"]:hover,
.stFormSubmitButton>button[kind="primary"]:hover,
button[kind="primary"]:hover{
  background:var(--as-primary-strong)!important;
  border-color:var(--as-primary-strong)!important;
}

/* Forms, expanders, alerts and tables */
[data-testid="stAlert"],
[data-testid="stExpander"]{
  border-radius:13px!important;
  border:1px solid var(--as-border)!important;
  box-shadow:none!important;
}
[data-testid="stExpander"] summary{
  font-weight:750!important;
}
[data-testid="stDataFrame"],
[data-testid="stTable"]{
  border:1px solid var(--as-border)!important;
  border-radius:14px!important;
  overflow:hidden!important;
  box-shadow:0 1px 2px rgba(16,24,40,.025)!important;
}
[data-testid="stDataFrame"] *{
  border-color:var(--as-border)!important;
}

/* Generic bordered Streamlit containers */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border-color:var(--as-border)!important;
  border-radius:15px!important;
}

/* Dialog / popover */
div[data-testid="stDialog"]{
  border-radius:18px!important;
}
div[data-testid="stPopover"]{
  border-radius:13px!important;
}

/* Keep Streamlit chrome quiet and product-like */
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
header[data-testid="stHeader"]{
  background:transparent!important;
}

/* Mobile */
@media(max-width:900px){
  .block-container{
    padding:.8rem .75rem 2rem!important;
  }
  div[data-baseweb="tab-list"]{
    overflow-x:auto!important;
    flex-wrap:nowrap!important;
    scrollbar-width:none!important;
  }
  div[data-baseweb="tab-list"]::-webkit-scrollbar{
    display:none!important;
  }
  button[data-baseweb="tab"]{
    flex:0 0 auto!important;
    font-size:.74rem!important;
    padding:8px 10px!important;
  }
  .dashboard-hero{
    padding:20px 18px!important;
  }
  [data-testid="stHorizontalBlock"]{
    gap:.65rem!important;
  }
  .stButton>button,
  .stDownloadButton>button,
  .stFormSubmitButton>button{
    min-height:44px!important;
  }
}

/* User-controlled dark mode */
body:has(.stApp) .stApp.dark-mode-placeholder{display:block;}
</style>
""",
        unsafe_allow_html=True,
    )

    if st.session_state.get("theme_toggle", False):
        st.markdown(
            """
<style>
.stApp{
  background:#0b0e13!important;
  color:#f5f7fa!important;
}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,
.section-title,.main-title{
  color:#f5f7fa!important;
}
.section-subtitle,.dashboard-hero-text,.mobile-nav-hint{
  color:#9aa3b2!important;
}
.dashboard-hero,.first-run-card,.max-ai-plan,.empty-state,
[data-testid="stMetric"],
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stTable"]{
  background:#11151d!important;
  border-color:#252b38!important;
  color:#f5f7fa!important;
}
.dashboard-hero-title,[data-testid="stMetricValue"]{
  color:#f5f7fa!important;
}
.stApp input,.stApp textarea,.stApp [data-baseweb="select"]>div{
  background:#11151d!important;
  border-color:#394152!important;
  color:#f5f7fa!important;
}
.stApp label,[data-testid="stMetricLabel"]{
  color:#9aa3b2!important;
}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{
  background:#11151d!important;
  border-color:#394152!important;
  color:#f5f7fa!important;
}
div[data-baseweb="tab-list"]{
  background:#11151d!important;
  border-color:#252b38!important;
}
button[data-baseweb="tab"]{
  color:#a8afbc!important;
}
button[data-baseweb="tab"][aria-selected="true"]{
  background:#272650!important;
  color:#c9c7ff!important;
}
button[data-baseweb="tab"][aria-selected="true"] *{
  color:#c9c7ff!important;
}
[data-testid="stAlert"],[data-testid="stExpander"]{
  border-color:#252b38!important;
}
div[data-testid="stVerticalBlockBorderWrapper"]{
  border-color:#252b38!important;
}
</style>
""",
            unsafe_allow_html=True,
        )
