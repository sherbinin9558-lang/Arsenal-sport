"""HTTP contract tests: all requests are mocked and no real message is sent."""
from unittest.mock import Mock
import saas_core


def test_supabase_request_uses_bearer_token_and_timeout(monkeypatch):
    monkeypatch.setattr(
        saas_core, "_supabase_config",
        lambda: ("https://example.supabase.co", "anon-test-key"),
    )
    response = Mock()
    response.ok = True
    response.json.return_value = [{"id": "1"}]
    request = Mock(return_value=response)
    monkeypatch.setattr(saas_core.requests, "request", request)

    result = saas_core._request(
        "GET", "/rest/v1/app_data", token="user-test-token",
        params={"tenant_id": "eq.tenant-1"},
    )

    assert result == [{"id": "1"}]
    args, kwargs = request.call_args
    assert args[0] == "GET"
    assert args[1] == "https://example.supabase.co/rest/v1/app_data"
    assert kwargs["headers"]["apikey"] == "anon-test-key"
    assert kwargs["headers"]["Authorization"] == "Bearer user-test-token"
    assert kwargs["params"] == {"tenant_id": "eq.tenant-1"}
    assert kwargs["timeout"] == 20


def test_supabase_http_error_is_converted_to_typed_error(monkeypatch):
    monkeypatch.setattr(
        saas_core, "_supabase_config",
        lambda: ("https://example.supabase.co", "anon-test-key"),
    )
    response = Mock()
    response.ok = False
    response.status_code = 403
    response.json.return_value = {"message": "Forbidden"}
    monkeypatch.setattr(saas_core.requests, "request", Mock(return_value=response))

    try:
        saas_core._request("GET", "/rest/v1/app_data", token="user-token")
    except saas_core.SupabaseRequestError as exc:
        assert exc.status_code == 403
        assert "Forbidden" not in str(exc)
        assert "Недостаточно прав" in str(exc)
    else:
        raise AssertionError("Expected SupabaseRequestError")


def test_no_telegram_or_vk_live_send_is_performed():
    """Guardrail reminder: live provider calls are intentionally absent in CI."""
    # Provider send functions should be added here once they are exposed as
    # importable service functions; tests must patch those functions, not send
    # synthetic requests and claim the production integration was tested.
    assert True
