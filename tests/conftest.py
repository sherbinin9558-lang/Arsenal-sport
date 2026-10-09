"""Shared fixtures for safe, network-free tests."""
import logging
import pytest


@pytest.fixture(autouse=True)
def capture_critical_logs(caplog):
    caplog.set_level(logging.ERROR)
    yield
    # Do not fail on expected errors deliberately asserted inside a test.
    # Individual tests may inspect caplog for unexpected critical messages.


@pytest.fixture
def isolated_state(monkeypatch):
    """Replace Streamlit session state with a normal dict for service tests."""
    import saas_core
    state = {}
    monkeypatch.setattr(saas_core.st, "session_state", state)
    return state
