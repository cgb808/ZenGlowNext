"""Tests for get_sanitized_env_snapshot in app.core.config.

Focus: ensure inclusion/exclusion rules behave as intended.
"""

from app.core.config import get_sanitized_env_snapshot


def test_env_snapshot_includes_allowed_prefixes(monkeypatch):
    monkeypatch.setenv("RAG_FUSION_LTR_WEIGHT", "0.7")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma:2b")
    snap = get_sanitized_env_snapshot()
    assert snap["RAG_FUSION_LTR_WEIGHT"] == "0.7"
    assert snap["OLLAMA_MODEL"] == "gemma:2b"


def test_env_snapshot_excludes_secret_markers(monkeypatch):
    monkeypatch.setenv("RAG_API_KEY", "supersecret")  # contains KEY
    monkeypatch.setenv("RAG_SERVICE_TOKEN", "tok123")  # contains TOKEN
    snap = get_sanitized_env_snapshot()
    assert "RAG_API_KEY" not in snap
    assert "RAG_SERVICE_TOKEN" not in snap


def test_env_snapshot_allows_supabase_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    snap = get_sanitized_env_snapshot()
    assert snap["SUPABASE_URL"] == "https://example.supabase.co"


def test_env_snapshot_truncates_long_values(monkeypatch):
    long_val = "x" * 250
    monkeypatch.setenv("RAG_LONG_VAL", long_val)
    snap = get_sanitized_env_snapshot()
    assert len(snap["RAG_LONG_VAL"]) < len(long_val)
    assert snap["RAG_LONG_VAL"].endswith("...")
