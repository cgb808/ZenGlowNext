import os
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_leonardo_status_endpoint():
    # Force fast path; external LLM call may be slow but should not raise.
    os.environ.setdefault("LLM_DEFAULT_PREFER", "leonardo")
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/leonardo/status")
    assert resp.status_code == 200
    data = resp.json()
    # Keys existence
    for key in [
        "leonardo_model",
        "tts_available",
        "speech_recognition",
        "status",
        "capabilities",
    ]:
        assert key in data
    assert isinstance(data["capabilities"], dict)
    # Status is one of expected states
    assert data["status"] in {"ready", "partial", "down", "error"}
