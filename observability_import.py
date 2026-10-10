"""Defensive import for a transient importlib KeyError observed in Streamlit Cloud."""


def load_observability():
    """Retry once only for the exact module-key failure; propagate other errors."""
    import importlib
    import sys
    try:
        return importlib.import_module("observability")
    except KeyError as exc:
        if exc.args != ("observability",):
            raise
        sys.modules.pop("observability", None)
        importlib.invalidate_caches()
        return importlib.import_module("observability")
