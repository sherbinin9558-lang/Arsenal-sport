"""ShopPilot AI visual system: dark blue Command Center, presentation only."""

SHOPPILOT_VISUAL_CSS = """
<style>
:root{--sp-bg:#071329;--sp-panel:#102b52;--sp-panel-2:#153765;--sp-line:rgba(132,177,235,.28);--sp-text:#f4f8ff;--sp-muted:#b8cbe7;--sp-blue:#66b9ff;--sp-violet:#897cff}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:linear-gradient(145deg,#071329 0%,#0b1d3a 48%,#0a1730 100%)!important;color:var(--sp-text)!important}
.block-container{max-width:1540px!important;padding:1.1rem clamp(1rem,2.4vw,2.5rem) 2.5rem!important}
[data-testid="stHeader"]{background:rgba(7,19,41,.94)!important}
[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stCaptionContainer"],label,[data-testid="stWidgetLabel"]{color:var(--sp-text)!important}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,
.stApp [data-testid="stMarkdownContainer"] strong,.stApp [data-testid="stMarkdownContainer"] b,
.stApp [data-testid="stText"],.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,.stApp label,
.stApp [data-testid="stWidgetLabel"],.stApp [data-testid="stCaptionContainer"]{color:var(--sp-text)!important}
[data-testid="stCaptionContainer"]{color:var(--sp-muted)!important}
/* Preserve the existing ShopPilot logo and its dark blue sidebar identity. */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#071329 0%,#0c2142 58%,#071329 100%)!important;border-right:1px solid var(--sp-line)!important}
section[data-testid="stSidebar"]>div:first-child{padding:1rem .8rem 1.4rem!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#e8f2ff!important}
section[data-testid="stSidebar"] hr{border-color:var(--sp-line)!important}
section[data-testid="stSidebar"] .sidebar-brand-title{color:#fff!important;font-size:1.5rem!important;letter-spacing:-.04em!important}
section[data-testid="stSidebar"] .sidebar-brand-version{color:#a8c8ed!important;letter-spacing:.13em!important}
section[data-testid="stSidebar"] .sidebar-brand-tagline{color:#c5d9f3!important}
section[data-testid="stSidebar"] .sidebar-max,section[data-testid="stSidebar"] .sidebar-quick-overview{background:linear-gradient(145deg,#123765,#10294e)!important;border:1px solid var(--sp-line)!important;border-radius:15px!important;box-shadow:0 10px 28px rgba(0,0,0,.2)!important}
section[data-testid="stSidebar"] .sidebar-max-kicker{color:#a9d8ff!important}
section[data-testid="stSidebar"] .sidebar-max-title,section[data-testid="stSidebar"] .sidebar-quick-title,section[data-testid="stSidebar"] .sidebar-quick-grid b{color:#fff!important}
section[data-testid="stSidebar"] .sidebar-max-text,section[data-testid="stSidebar"] .sidebar-quick-grid span,section[data-testid="stSidebar"] .sidebar-quick-note{color:#c1d5ef!important}
section[data-testid="stSidebar"] .sidebar-quick-grid>div{background:rgba(255,255,255,.07)!important;border:1px solid rgba(174,205,241,.2)!important}
section[data-testid="stSidebar"] button[kind="primary"]{background:linear-gradient(110deg,#57baf5,#7c8cff)!important;color:#071329!important;border:0!important;border-radius:10px!important;font-weight:850!important}
section[data-testid="stSidebar"] [data-testid="stExpander"],section[data-testid="stSidebar"] [data-testid="stAlert"]{background:#10294e!important;border:1px solid var(--sp-line)!important;border-radius:12px!important}
section[data-testid="stSidebar"] [data-testid="stAlert"] *{color:#e8f2ff!important}
/* Native workspace tabs remain functional; visual treatment follows the reference. */
.st-key-main_workspace_tabs{margin:.35rem 0 1.1rem!important}
.st-key-main_workspace_tabs [data-baseweb="tab-list"]{display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;gap:5px!important;padding:6px!important;border-radius:13px!important;background:#0d2445!important;border:1px solid var(--sp-line)!important}
.st-key-main_workspace_tabs [data-baseweb="tab"]{flex:0 0 auto!important;min-height:40px!important;padding:0 13px!important;border:1px solid transparent!important;border-radius:9px!important;color:#d5e7fc!important;font-weight:750!important;background:transparent!important}
.st-key-main_workspace_tabs [data-baseweb="tab"][aria-selected="true"],.st-key-main_workspace_tabs [data-baseweb="tab"][aria-selected="true"] *{color:#fff!important;background:linear-gradient(110deg,#1760a5,#267fc1)!important;border-color:rgba(135,197,255,.45)!important;box-shadow:0 4px 14px rgba(0,0,0,.18)!important}
/* Wide hero: the existing robot asset is displayed at the right, copy at the left. */
/* Single banner wrapper matches the approved laptop reference. */
.st-key-dashboard_hero_shell{padding:14px 16px!important;border:1px solid rgba(115,177,240,.42)!important;border-radius:20px!important;background:linear-gradient(112deg,#10427c 0%,#10508e 54%,#173b70 100%)!important;box-shadow:0 14px 34px rgba(0,0,0,.2)!important;overflow:hidden!important}
.st-key-dashboard_hero_shell [data-testid="stHorizontalBlock"]{align-items:center!important;gap:14px!important}
.dashboard-hero{min-height:220px!important;display:flex!important;flex-direction:column!important;justify-content:center!important;padding:clamp(12px,1.8vw,24px)!important;background:transparent!important;border:0!important;box-shadow:none!important}
.dashboard-hero-kicker{color:#b9dcff!important;font-size:.65rem!important;letter-spacing:.17em!important;font-weight:850!important}
.dashboard-hero-title{color:#fff!important;font-size:clamp(1.8rem,3vw,2.7rem)!important;line-height:1.04!important;letter-spacing:-.045em!important;font-weight:900!important}
.dashboard-hero-gradient{color:#e6f3ff!important;background:none!important}
.dashboard-hero-text{color:#d7eaff!important;font-size:.92rem!important;line-height:1.5!important;max-width:560px!important}
.st-key-shoppilot_hero_art{min-height:220px!important;display:flex!important;align-items:stretch!important;justify-content:center!important}
.st-key-shoppilot_hero_art img{width:100%!important;height:100%!important;min-height:220px!important;max-height:300px!important;object-fit:cover!important;border-radius:17px!important;border:1px solid rgba(137,190,245,.4)!important;box-shadow:0 14px 30px rgba(0,0,0,.22)!important}
/* Guide and first-run panels retain the same blue family. */
.owner-guide-card,.first-run-card{margin:1rem 0!important;padding:18px 20px!important;border:1px solid var(--sp-line)!important;border-radius:16px!important;background:linear-gradient(145deg,#102b52,#12345f)!important;box-shadow:0 8px 22px rgba(0,0,0,.12)!important}
.owner-guide-kicker,.first-run-kicker{color:#9fd3ff!important;font-size:.66rem!important;letter-spacing:.15em!important;font-weight:900!important}
.owner-guide-title,.first-run-title{color:#fff!important;font-size:1.1rem!important;font-weight:850!important}
.owner-guide-grid>div{background:rgba(255,255,255,.055)!important;border:1px solid rgba(167,201,238,.2)!important;border-radius:11px!important;padding:12px!important}
.owner-guide-grid b{color:#fff!important}.owner-guide-grid span,.owner-guide-note,.first-run-text{color:#c4d8f1!important}
/* Dashboard KPI tiles and content surfaces. */
[data-testid="stMetric"]{background:linear-gradient(145deg,#123765,#174477)!important;border:1px solid rgba(127,184,239,.42)!important;border-radius:14px!important;padding:13px 15px!important;box-shadow:0 7px 18px rgba(0,0,0,.14)!important}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] *{color:#d5e9ff!important;font-weight:700!important}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:#fff!important;font-weight:850!important}
[data-testid="stMetricDelta"]{color:#b8dfff!important}
[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stDataFrame"],[data-testid="stTable"],[data-testid="stExpander"]{border:1px solid var(--sp-line)!important;border-radius:13px!important;background:#10294e!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary *{color:#eaf3ff!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{border-radius:10px!important;border-color:rgba(139,181,226,.4)!important;background:#0b2040!important;color:#fff!important}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder{color:#9db4d1!important}
.stButton>button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button{min-height:39px!important;border-radius:10px!important;font-weight:750!important;border:1px solid rgba(135,183,232,.38)!important;background:#153b68!important;color:#f5f9ff!important}
.stButton>button:hover,[data-testid="stDownloadButton"] button:hover{border-color:#80c7ff!important;box-shadow:0 6px 16px rgba(0,0,0,.18)!important}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:linear-gradient(110deg,#1678bd,#347ed1)!important;color:#fff!important;border:1px solid rgba(159,210,255,.5)!important}
[data-testid="stAlert"]{background:#12345e!important;border:1px solid var(--sp-line)!important;border-radius:12px!important}
[data-testid="stAlert"] *{color:#edf6ff!important}
.section-kicker{color:#9fd3ff!important;letter-spacing:.15em!important;font-weight:900!important}
.section-title{color:#fff!important;font-size:clamp(1.5rem,2.3vw,2.1rem)!important;font-weight:900!important}
.section-subtitle{color:#c1d5ed!important}
:focus-visible{outline:2px solid #8dccff!important;outline-offset:2px!important}
@media(max-width:900px){.block-container{padding:.8rem 1rem 2rem!important}.st-key-dashboard_hero_shell{padding:10px!important}.dashboard-hero{min-height:190px!important}.st-key-shoppilot_hero_art{min-height:170px!important}.st-key-shoppilot_hero_art img{min-height:160px!important;max-height:220px!important}}
@media(max-width:640px){.st-key-dashboard_hero_shell{padding:9px!important}.dashboard-hero{min-height:0!important;padding:19px 16px!important;border-radius:15px!important}.dashboard-hero-title{font-size:1.8rem!important}.owner-guide-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.st-key-main_workspace_tabs [data-baseweb="tab"]{min-height:42px!important;padding:0 10px!important}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
"""

def apply_shoppilot_visual_system(streamlit_module, dark_mode=True):
    """Apply the approved dark Command Center only when the dark theme is selected."""
    if not dark_mode:
        return
    streamlit_module.markdown(SHOPPILOT_VISUAL_CSS, unsafe_allow_html=True)
