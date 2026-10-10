import importlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from observability_import import load_observability


def test_retries_exact_observability_keyerror_once():
    expected = SimpleNamespace(
        configure_observability=lambda: None,
        install_exception_hook=lambda: None,
    )
    with patch.object(importlib, "import_module", side_effect=[KeyError("observability"), expected]) as mocked:
        assert load_observability() is expected
    assert mocked.call_count == 2


def test_does_not_retry_unrelated_keyerror():
    with patch.object(importlib, "import_module", side_effect=KeyError("other_module")) as mocked:
        with pytest.raises(KeyError, match="other_module"):
            load_observability()
    assert mocked.call_count == 1


def test_propagates_failure_on_retry():
    with patch.object(importlib, "import_module", side_effect=[KeyError("observability"), RuntimeError("still broken")]) as mocked:
        with pytest.raises(RuntimeError, match="still broken"):
            load_observability()
    assert mocked.call_count == 2
