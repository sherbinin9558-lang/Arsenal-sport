"""Supabase transport errors must not leak backend response bodies."""
import pytest
import saas_core


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = False
        self.headers = {}
        self.text = "PRIVATE_BACKEND_DETAIL service_role_key=do-not-leak"
        self._payload = payload or {"message": self.text}

    def json(self):
        return self._payload


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 409, 422, 429, 500, 503])
def test_request_sanitizes_backend_error_body(monkeypatch, status_code):
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("https://example.supabase.co", "anon-test-key"))
    monkeypatch.setattr(saas_core.requests, "request", lambda *args, **kwargs: FakeResponse(status_code))
    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._request("GET", "/rest/v1/app_data")
    assert exc.value.status_code == status_code
    assert "PRIVATE_BACKEND_DETAIL" not in str(exc.value)
    assert "service_role_key" not in str(exc.value)


def test_paged_request_sanitizes_backend_error_body(monkeypatch):
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("https://example.supabase.co", "anon-test-key"))
    monkeypatch.setattr(saas_core.requests, "get", lambda *args, **kwargs: FakeResponse(500))
    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._rest_get_paged("/rest/v1/app_data", "test-access-token")
    assert exc.value.status_code == 500
    assert "PRIVATE_BACKEND_DETAIL" not in str(exc.value)
    assert "service_role_key" not in str(exc.value)


def test_conflict_marker_is_kept_as_internal_code_not_user_message(monkeypatch):
    payload = {"message": "DATA_CONFLICT: PRIVATE_BACKEND_DETAIL", "code": "P0001"}
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("https://example.supabase.co", "anon-test-key"))
    monkeypatch.setattr(saas_core.requests, "request", lambda *args, **kwargs: FakeResponse(409, payload))
    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._request("POST", "/rest/v1/rpc/save_app_data_batch")
    assert exc.value.error_code == "DATA_CONFLICT"
    assert "DATA_CONFLICT" not in str(exc.value)
    assert "PRIVATE_BACKEND_DETAIL" not in str(exc.value)


def test_paged_request_preserves_conflict_marker_internally(monkeypatch):
    payload = {"message": "RECORD_NOT_FOUND: PRIVATE_BACKEND_DETAIL"}
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("https://example.supabase.co", "anon-test-key"))
    monkeypatch.setattr(saas_core.requests, "get", lambda *args, **kwargs: FakeResponse(409, payload))
    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._rest_get_paged("/rest/v1/app_data", "test-access-token")
    assert exc.value.error_code == "RECORD_NOT_FOUND"
    assert "RECORD_NOT_FOUND" not in str(exc.value)
    assert "PRIVATE_BACKEND_DETAIL" not in str(exc.value)
