import io
import pytest
from fastapi.testclient import TestClient

from app.app_factory import create_app

app = create_app()
client = TestClient(app)


class DummyFile(io.BytesIO):
    filename = "sample.wav"


def _override_dependencies(db_impl, redis_impl=None):
    """Helper to register dependency overrides for the transcription router.

    We must override the original dependency callables captured by Depends({...}).
    """
    from app.audio import transcription_jobs_router as tj  # local import for each use

    original_db = tj.get_db_client  # the callable object referenced by Depends
    original_redis = tj.get_redis_client

    async def _db_dep():  # returns provided impl
        return db_impl()

    if redis_impl is not None:
        async def _redis_dep():  # type: ignore
            return redis_impl()
    else:  # pragma: no cover - provide benign stub
        async def _redis_dep():  # type: ignore
            class _NoRedis:  # minimal stub
                async def set(self, *_a, **_kw):
                    return True
                async def xadd(self, *_a, **_kw):
                    return "0-0"
            return _NoRedis()

    app.dependency_overrides[original_db] = _db_dep
    app.dependency_overrides[original_redis] = _redis_dep


def test_transcription_job_creation():
    try:
        from app.audio import transcription_jobs_router as tj  # noqa: F401
    except Exception:
        pytest.skip("transcription jobs router not available")

    class _DB:
        async def execute(self, *_a, **_kw):
            return None
        async def fetch_all(self, *_a, **_kw):
            return [{"status": "pending", "transcript": None}]

    class _Redis:
        async def set(self, *_a, **_kw):
            return True
        async def xadd(self, *_a, **_kw):
            return "0-0"

    _override_dependencies(_DB, _Redis)

    file_content = b"RIFF....WAVEfmt "
    response = client.post(
        "/audio/transcribe/job",
        files={"file": ("sample.wav", file_content, "audio/wav")},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    status_resp = client.get(f"/audio/transcribe/job/status/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "pending"


def test_transcription_status_not_found():
    """Unknown job id returns 404 when DB returns no rows."""
    try:
        from app.audio import transcription_jobs_router as tj  # noqa: F401
    except Exception:
        pytest.skip("transcription jobs router not available")

    class _EmptyDB:
        async def execute(self, *_a, **_kw):
            return None
        async def fetch_all(self, *_a, **_kw):
            return []

    class _Redis:
        async def set(self, *_a, **_kw):  # pragma: no cover - unused in this test
            return True
        async def xadd(self, *_a, **_kw):  # pragma: no cover - unused
            return "0-0"

    _override_dependencies(_EmptyDB, _Redis)

    status_resp = client.get("/audio/transcribe/job/status/does-not-exist")
    assert status_resp.status_code == 404
