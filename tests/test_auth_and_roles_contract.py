"""Focused security contracts. No real credentials or Supabase calls are used."""
import pytest
import saas_core


@pytest.mark.unit
def test_data_entity_validation_rejects_path_traversal():
    for value in ("../users", "products/../../secrets", "", " "):
        with pytest.raises(ValueError):
            saas_core._validate_data_entity(value)


@pytest.mark.unit
def test_request_refuses_missing_supabase_url(monkeypatch):
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("", "anon-test-key"))
    with pytest.raises(saas_core.SupabaseRequestError, match="SUPABASE_URL"):
        saas_core._request("GET", "/rest/v1/app_data")


@pytest.mark.unit
def test_request_refuses_missing_anon_key(monkeypatch):
    monkeypatch.setattr(saas_core, "_supabase_config", lambda: ("https://example.supabase.co", ""))
    with pytest.raises(saas_core.SupabaseRequestError, match="SUPABASE_ANON_KEY"):
        saas_core._request("GET", "/rest/v1/app_data")
