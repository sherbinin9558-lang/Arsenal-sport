"""Regression contracts for user-visible integration errors."""
import ast
from pathlib import Path


def _function(name):
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    return next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _calls_named(node, name):
    return [
        call for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == name
    ]


def test_telegram_photo_requires_provider_success_flag():
    function = _function("publish_to_telegram")
    source = ast.get_source_segment(Path("app.py").read_text(encoding="utf-8"), function)
    assert 'payload.get("ok") is True' in source
    assert _calls_named(function, "safe_error_text")


def test_telegram_and_vk_reels_sanitize_provider_errors():
    for name in ("publish_reel_to_telegram", "publish_reel_to_vk"):
        function = _function(name)
        assert _calls_named(function, "safe_error_text"), name


def test_ui_exception_messages_use_sanitizer():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "st.error(str(e))" not in source
    assert 'st.warning(f"Статус оплаты пока не подтверждён: {e}")' not in source
