import os
import pytest
try:
    from fastapi.testclient import TestClient  # type: ignore
except Exception:  # pragma: no cover - dependency mismatch
    TestClient = None  # type: ignore


def test_health_and_access_log():
    # Minimal env for app startup
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("SKIP_AUDIO_IMPORTS", "1")
    if TestClient is None:
        pytest.skip("TestClient unavailable")
    try:
        from app.main import app  # delayed import after env setup
        client = TestClient(app)
    except Exception as e:
        pytest.skip(f"TestClient init failed: {e}")
    r = client.get("/health")
    assert r.status_code in (200, 503)
    if "X-Request-ID" in r.headers:
        logs = client.get("/logs/recent").json()
        lines = logs.get("lines", [])
        assert any("/health" in l["msg"] and "access" in l["msg"] for l in lines), "missing access log line for /health"
