"""ShopPilot AI visual system: presentation only; existing Streamlit widgets retain behavior."""

SHOPPILOT_VISUAL_CSS = """
<style>
:root{--sp-canvas:#f2f5fb;--sp-line:#e1e7f1;--sp-ink:#15203b;--sp-muted:#68758d;--sp-accent:#665be0}
.stApp,[data-testid="stAppViewContainer"]{background:var(--sp-canvas)!important}
.block-container{max-width:1540px!important;padding:1.35rem clamp(1rem,2.4vw,2.5rem) 3rem!important}
[data-testid="stHeader"]{background:rgba(242,245,251,.9)!important}
/* Branded dark navigation rail */
section[data-testid="stSidebar"]{background:radial-gradient(ellipse at 18% 0%,rgba(91,112,218,.22),transparent 38%),linear-gradient(180deg,#080e20,#101a35 52%,#080e20)!important;border-right:1px solid rgba(132,151,204,.22)!important}
section[data-testid="stSidebar"]>div:first-child{padding:1.1rem .85rem 1.5rem!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#e5ebff!important}
section[data-testid="stSidebar"] hr{border-color:rgba(164,180,226,.18)!important}
section[data-testid="stSidebar"] .sidebar-brand-title{color:#fff!important;font-size:1.65rem!important;letter-spacing:-.05em!important}
section[data-testid="stSidebar"] .sidebar-brand-version{color:#9eafd5!important;letter-spacing:.16em!important}
section[data-testid="stSidebar"] .sidebar-brand-tagline{color:#c4d0ef!important}
section[data-testid="stSidebar"] .sidebar-max{padding:1rem!important;border-radius:18px!important;background:linear-gradient(145deg,rgba(54,67,130,.72),rgba(24,31,69,.96))!important;border:1px solid rgba(151,139,255,.48)!important;box-shadow:0 15px 36px rgba(0,0,0,.25)!important}
section[data-testid="stSidebar"] .sidebar-max-kicker{color:#c2b7ff!important;letter-spacing:.18em!important}
section[data-testid="stSidebar"] .sidebar-max-title{color:#fff!important;font-size:1.45rem!important}
section[data-testid="stSidebar"] .sidebar-max-text{color:#d0d8f5!important}
section[data-testid="stSidebar"] button[kind="primary"]{min-height:45px!important;border-radius:13px!important;background:linear-gradient(105deg,#68c9f2,#9582ff)!important;color:#09132d!important;border:0!important;font-weight:850!important}
section[data-testid="stSidebar"] .st-key-sidebar_preferences [data-testid="stExpander"],section[data-testid="stSidebar"] .st-key-sidebar_store_context [data-testid="stAlert"]{background:rgba(255,255,255,.045)!important;border:1px solid rgba(155,174,225,.2)!important;border-radius:13px!important}
section[data-testid="stSidebar"] .sidebar-quick-overview{background:linear-gradient(145deg,#172344,#202b50)!important;border:1px solid rgba(151,139,255,.42)!important;border-radius:16px!important}
section[data-testid="stSidebar"] .sidebar-quick-kicker{color:#bdb1ff!important}
section[data-testid="stSidebar"] .sidebar-quick-title,section[data-testid="stSidebar"] .sidebar-quick-grid b{color:#fff!important}
section[data-testid="stSidebar"] .sidebar-quick-grid>div{background:rgba(255,255,255,.07)!important;border:1px solid rgba(185,199,236,.18)!important}
section[data-testid="stSidebar"] .sidebar-quick-grid span,section[data-testid="stSidebar"] .sidebar-quick-note{color:#c7d1ec!important}
/* Command navigation keeps native Streamlit tabs and their callbacks */
.st-key-main_workspace_tabs{margin:.5rem 0 1.3rem!important}
.st-key-main_workspace_tabs [data-baseweb="tab-list"]{display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;gap:6px!important;padding:7px!important;border-radius:16px!important;background:#fff!important;border:1px solid var(--sp-line)!important;box-shadow:0 5px 20px rgba(24,39,75,.055)!important}
.st-key-main_workspace_tabs [data-baseweb="tab"]{flex:0 0 auto!important;min-height:42px!important;padding:0 15px!important;border:1px solid transparent!important;border-radius:11px!important;color:#59657e!important;font-weight:750!important;background:transparent!important}
.st-key-main_workspace_tabs [data-baseweb="tab"][aria-selected="true"]{color:#fff!important;background:linear-gradient(110deg,#5149c9,#7669ed)!important;box-shadow:0 5px 15px rgba(92,81,211,.24)!important}
/* Hero and robot */
.dashboard-hero{min-height:260px!important;display:flex!important;flex-direction:column!important;justify-content:center!important;padding:clamp(24px,3vw,42px)!important;border:1px solid rgba(145,164,255,.3)!important;border-radius:24px!important;background:radial-gradient(circle at 90% 15%,rgba(140,111,255,.3),transparent 31%),linear-gradient(120deg,#091329,#14264b 62%,#29204d)!important;box-shadow:0 18px 42px rgba(19,31,68,.16)!important}
.dashboard-hero-kicker{color:#b8c9ff!important;font-size:.68rem!important;letter-spacing:.19em!important;font-weight:850!important}
.dashboard-hero-title{color:#fff!important;font-size:clamp(2rem,3.2vw,3.4rem)!important;line-height:1.02!important;letter-spacing:-.05em!important;font-weight:900!important}
.dashboard-hero-text{color:#d1dcf5!important;font-size:1rem!important;line-height:1.6!important;max-width:650px!important}
.dashboard-hero-gradient{background:linear-gradient(90deg,#70d6ff,#9b91ff,#d3a3ff);-webkit-background-clip:text;background-clip:text;color:transparent!important}
.st-key-shoppilot_hero_art{min-height:260px!important;display:flex!important;align-items:center!important;justify-content:center!important}
.st-key-shoppilot_hero_art img{width:100%!important;max-height:340px!important;object-fit:cover!important;border-radius:22px!important;border:1px solid rgba(137,159,236,.3)!important;box-shadow:0 18px 40px rgba(18,28,61,.15)!important}
.owner-guide-card{margin:1rem 0 1.2rem!important;padding:20px 22px!important;border:1px solid #dce4f1!important;border-radius:19px!important;background:linear-gradient(135deg,#fff,#f7f8ff)!important;box-shadow:0 8px 24px rgba(26,39,76,.055)!important}
.owner-guide-kicker,.first-run-kicker{color:#6255d9!important;font-size:.68rem!important;letter-spacing:.16em!important;font-weight:900!important}
.owner-guide-title{color:#17213b!important;font-size:1.18rem!important;font-weight:850!important}
.owner-guide-grid>div{background:#fff!important;border:1px solid #e4e9f3!important;border-radius:13px!important;padding:13px!important}
.owner-guide-grid b{color:#1a2440!important}.owner-guide-grid span,.owner-guide-note{color:#68748d!important}
/* Unified cards, metrics, forms, tables and controls */
[data-testid="stMetric"],[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px!important;border-color:#e1e7f1!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#f9faff)!important;padding:14px 16px!important;box-shadow:0 5px 18px rgba(25,39,76,.045)!important}
[data-testid="stMetricLabel"]{color:#66728a!important;font-weight:700!important}[data-testid="stMetricValue"]{color:#182342!important;font-weight:850!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--sp-line)!important;border-radius:14px!important;overflow:hidden!important}
[data-testid="stExpander"]{border:1px solid #e1e7f1!important;border-radius:14px!important;background:#fff!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{border-radius:11px!important;border-color:#d7dfed!important;background:#fff!important}
.stButton>button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button{min-height:40px!important;border-radius:11px!important;font-weight:750!important;border-color:#d8dfed!important;transition:transform .16s ease,box-shadow .16s ease!important}
.stButton>button:hover,[data-testid="stDownloadButton"] button:hover{transform:translateY(-1px);box-shadow:0 7px 18px rgba(37,51,91,.1)!important}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:linear-gradient(110deg,#5750cf,#7c70ee)!important;color:#fff!important;border:0!important}
[data-testid="stAlert"]{border-radius:13px!important}
.section-kicker{color:#665be0!important;letter-spacing:.16em!important;font-weight:900!important}
.section-title{color:#15203a!important;font-size:clamp(1.6rem,2.4vw,2.25rem)!important;font-weight:900!important;letter-spacing:-.04em!important}
.section-subtitle{color:#69758d!important;margin-bottom:1rem!important}
:focus-visible{outline-color:#7469ed!important}
@media(max-width:900px){.block-container{padding:.8rem 1rem 2rem!important}.dashboard-hero{min-height:200px!important}.st-key-shoppilot_hero_art{min-height:180px!important}.st-key-shoppilot_hero_art img{max-height:240px!important}}
@media(max-width:640px){.dashboard-hero{min-height:0!important;padding:22px 18px!important;border-radius:18px!important}.dashboard-hero-title{font-size:2rem!important}.owner-guide-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.st-key-main_workspace_tabs [data-baseweb="tab"]{min-height:44px!important;padding:0 12px!important}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
"""

def apply_shoppilot_visual_system(streamlit_module):
    """Apply visual styling without changing widget behavior."""
    streamlit_module.markdown(SHOPPILOT_VISUAL_CSS, unsafe_allow_html=True)
