"""Visual styling for the existing Streamlit workspace navigation.

This module changes presentation only. The tab labels, order, permissions and
rendered page containers remain owned by app.py.
"""

WORKSPACE_NAV_CSS = """
<style>
.st-key-main_workspace_tabs [data-baseweb="tab-list"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 7px !important;
    max-width: 100% !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    padding: 5px 3px 9px !important;
    border-bottom: 1px solid rgba(125, 135, 160, .22) !important;
    scrollbar-width: thin;
    overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch;
}
.st-key-main_workspace_tabs [data-baseweb="tab"] {
    flex: 0 0 auto !important;
    min-height: 40px !important;
    padding: 0 15px !important;
    border: 1px solid transparent !important;
    border-radius: 11px !important;
    background: transparent !important;
    color: inherit !important;
    font-weight: 750 !important;
    white-space: nowrap !important;
    transition: background .16s ease, border-color .16s ease, transform .16s ease !important;
}
.st-key-main_workspace_tabs [data-baseweb="tab"]:hover {
    background: rgba(91, 92, 226, .075) !important;
    border-color: rgba(91, 92, 226, .18) !important;
}
.st-key-main_workspace_tabs [data-baseweb="tab"][aria-selected="true"] {
    color: #382477 !important;
    background: linear-gradient(135deg, rgba(236, 231, 255, .98), rgba(224, 231, 255, .92)) !important;
    border-color: rgba(117, 96, 205, .32) !important;
    box-shadow: 0 4px 13px rgba(55, 45, 110, .09) !important;
}
.st-key-main_workspace_tabs [data-baseweb="tab"]:focus-visible {
    outline: 3px solid rgba(91, 92, 226, .48) !important;
    outline-offset: 2px !important;
}
@media (max-width: 768px) {
    .st-key-main_workspace_tabs [data-baseweb="tab-list"] {
        gap: 5px !important;
        padding: 4px 2px 8px !important;
        scroll-snap-type: x proximity;
    }
    .st-key-main_workspace_tabs [data-baseweb="tab"] {
        min-height: 42px !important;
        padding: 0 12px !important;
        scroll-snap-align: start;
    }
}
@media (prefers-reduced-motion: reduce) {
    .st-key-main_workspace_tabs [data-baseweb="tab"] {
        transition: none !important;
    }
}
</style>
"""


def apply_workspace_navigation_styles(streamlit_module):
    """Apply styling to the main workspace tabs without changing their behavior."""
    streamlit_module.markdown(WORKSPACE_NAV_CSS, unsafe_allow_html=True)
