"""Supabase transport errors must not leak backend response bodies."""
import pytest
import saas_core


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = False
        self.headers = {}
        self.text = 'PRIVATE_BACKEND_DETAIL service_role_key=do-not-leak'
        self._payload = payload or {'message': self.text}

    def json(self):
        return self._payload


@pytest.mark.parametrize('status_code', [400, 401, 403, 404, 409, 422, 429, 500, 503])
def test_request_sanitizes_backend_error_body(monkeypatch, status_code):
    monkeypatch.setattr(saas_core, '_supabase_config', lambda: ('https://example.supabase.co', 'anon-test-key'))
    monkeypatch.setattr(saas_core.requests, 'request', lambda *args, **kwargs: FakeResponse(status_code))

    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._request('GET', '/rest/v1/app_data')

    assert exc.value.status_code == status_code
    assert 'PRIVATE_BACKEND_DETAIL' not in str(exc.value)
    assert 'service_role_key' not in str(exc.value)
    assert str(exc.value)


def test_paged_request_sanitizes_backend_error_body(monkeypatch):
    monkeypatch.setattr(saas_core, '_supabase_config', lambda: ('https://example.supabase.co', 'anon-test-key'))
    monkeypatch.setattr(saas_core.requests, 'get', lambda *args, **kwargs: FakeResponse(500))

    with pytest.raises(saas_core.SupabaseRequestError) as exc:
        saas_core._rest_get_paged('/rest/v1/app_data', 'test-access-token')

    assert exc.value.status_code == 500
    assert 'PRIVATE_BACKEND_DETAIL' not in str(exc.value)
    assert 'service_role_key' not in str(exc.value)
