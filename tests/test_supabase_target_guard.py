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
