"""Unit tests for the fail-closed Supabase RLS target guard."""

import pytest

from scripts.supabase_rls_integration import validate_supabase_target


@pytest.mark.parametrize(
    "url",
    [
        "https://qibncofxwuhasekwyffs.supabase.co",
        "https://qibncofxwuhasekwyffs.supabase.co/",
        "https://qibncofxwuhasekwyffs.supabase.co:443",
    ],
)
def test_accepts_only_canonical_test_project_urls(url: str) -> None:
    validate_supabase_target(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://qibncofxwuhasekwyffs.supabase.co",
        "https://other-project.supabase.co",
        "https://qibncofxwuhasekwyffs.supabase.co.evil.example",
        "https://user@qibncofxwuhasekwyffs.supabase.co",
        "https://user:password@qibncofxwuhasekwyffs.supabase.co",
        "https://qibncofxwuhasekwyffs.supabase.co:444",
    ],
)
def test_rejects_unsafe_supabase_targets(url: str) -> None:
    with pytest.raises(RuntimeError, match="Refusing RLS integration tests"):
        validate_supabase_target(url)


class _Response:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400


class _CleanupApi:
    def __init__(self):
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs.get("params")))
        if path == "/rest/v1/invitations" and kwargs.get("params", {}).get("tenant_id") == "eq.tenant-a":
            return _Response(500)
        if path == "/auth/v1/admin/users/user-a":
            return _Response(503)
        return _Response(204)


def test_cleanup_attempts_every_resource_and_reports_failed_deletes() -> None:
    from scripts.supabase_rls_integration import cleanup_test_data

    api = _CleanupApi()
    errors = cleanup_test_data(api, ["tenant-a", "tenant-b"], ["user-a", "user-b"])

    assert len(api.calls) == 10
    assert errors == ["invitations: AssertionError", "auth user: AssertionError"]
    assert ("DELETE", "/rest/v1/tenants", {"id": "eq.tenant-b"}) in api.calls
    assert ("DELETE", "/auth/v1/admin/users/user-b", None) in api.calls
