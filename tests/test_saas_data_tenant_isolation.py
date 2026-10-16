"""Tests the real saas_core data-loading query contract with network mocked."""
import saas_core


def test_data_load_scopes_query_to_current_tenant_and_entity(monkeypatch, isolated_state):
    captured = {}
    monkeypatch.setattr(saas_core, "saas_enabled", lambda: True)
    monkeypatch.setattr(saas_core, "tenant_id", lambda: "tenant-alpha")

    def fake_rest_get(path, token, params=None):
        captured.update(path=path, token=token, params=params)
        return [{
            "record_id": "record-1",
            "payload": {"name": "Training shirt"},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }]

    monkeypatch.setattr(saas_core, "_rest_get", fake_rest_get)
    isolated_state["saas_access_token"] = "test-access-token"

    result = saas_core.data_load("products", [])

    assert captured["path"] == "/rest/v1/app_data"
    assert captured["token"] == "test-access-token"
    assert captured["params"]["tenant_id"] == "eq.tenant-alpha"
    assert captured["params"]["entity"] == "eq.products"
    assert result[0]["name"] == "Training shirt"


def test_data_load_does_not_return_rows_for_an_empty_tenant(monkeypatch, isolated_state):
    monkeypatch.setattr(saas_core, "saas_enabled", lambda: True)
    monkeypatch.setattr(saas_core, "tenant_id", lambda: "tenant-beta")
    calls = []

    def fake_rest_get(path, token, params=None):
        calls.append(params)
        assert params["tenant_id"] == "eq.tenant-beta"
        return []

    monkeypatch.setattr(saas_core, "_rest_get", fake_rest_get)
    isolated_state["saas_access_token"] = "test-token"

    assert saas_core.data_load("products", []) == []
    assert calls


def test_invalid_entity_name_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        saas_core.data_load("../products", [])


def test_data_save_scopes_atomic_write_to_current_tenant(monkeypatch, isolated_state):
    captured = {}
    monkeypatch.setattr(saas_core, "saas_enabled", lambda: True)
    monkeypatch.setattr(saas_core, "tenant_id", lambda: "tenant-alpha")
    monkeypatch.setattr(saas_core, "can", lambda permission: True)
    monkeypatch.setattr(saas_core, "_rest_post", lambda path, token, payload: captured.update(
        path=path, token=token, payload=payload
    ))
    monkeypatch.setattr(saas_core, "data_load", lambda entity, default: default)
    isolated_state["saas_access_token"] = "test-access-token"

    saas_core.data_save("products", [{"name": "New product"}])

    assert captured["path"] == "/rest/v1/rpc/save_app_data_batch"
    assert captured["token"] == "test-access-token"
    assert captured["payload"]["p_tenant_id"] == "tenant-alpha"
    assert captured["payload"]["p_entity"] == "products"
    assert len(captured["payload"]["p_rows"]) == 1
    assert captured["payload"]["p_rows"][0]["is_new"] is True


def test_viewer_cannot_write_records(monkeypatch, isolated_state):
    monkeypatch.setattr(saas_core, "saas_enabled", lambda: True)
    monkeypatch.setattr(saas_core, "tenant_id", lambda: "tenant-alpha")
    monkeypatch.setattr(saas_core, "can", lambda permission: False)
    calls = []
    monkeypatch.setattr(saas_core, "_rest_post", lambda *args, **kwargs: calls.append(args))

    import pytest
    with pytest.raises(PermissionError, match="нет прав"):
        saas_core.data_save("products", [{"name": "Must not save"}])
    assert calls == []


def test_non_admin_cannot_write_shop_settings(monkeypatch, isolated_state):
    monkeypatch.setattr(saas_core, "saas_enabled", lambda: True)
    monkeypatch.setattr(saas_core, "tenant_id", lambda: "tenant-alpha")
    monkeypatch.setattr(saas_core, "can", lambda permission: permission != "settings")
    calls = []
    monkeypatch.setattr(saas_core, "_rest_post", lambda *args, **kwargs: calls.append(args))

    import pytest
    with pytest.raises(PermissionError, match="Только администратор или владелец"):
        saas_core.data_save("settings", [{"theme": "dark"}])
    assert calls == []
