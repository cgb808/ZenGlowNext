import os
import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore


def test_gpu_probe_disabled_by_default():
    """When ENABLE_GPU_PROBE is not set, metrics should report empty gpus list."""
    if TestClient is None:
        pytest.skip("TestClient unavailable")
    # Ensure probe not enabled
    os.environ.pop("ENABLE_GPU_PROBE", None)
    from api.main import app  # type: ignore
    client = TestClient(app)
    r = client.get("/metrics/sys")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("gpus"), list)
    assert data["gpus"] == []
