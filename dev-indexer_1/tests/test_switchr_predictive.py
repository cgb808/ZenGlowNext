import os
import importlib
import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _reload_for_flag(flag: str):
    os.environ["ENABLE_ROUTE_CALIB"] = flag
    import app.central_control.switchr_router as sr
    importlib.reload(sr)  # re-evaluate flag + controller
    return sr


async def _route(client: AsyncClient, text: str, **kw):
    payload = {"text": text, **kw}
    return await client.post("/switchr/route", json=payload)


async def test_route_calibration_toggle():
    # Test disabled state
    flag, expect_enabled = "0", False
    sr = await _reload_for_flag(flag)
    from app.main import app  # import after reload to pick updated router module state
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await _route(client, "Explain the integral of a matrix function")
        assert r.status_code == 200
        data = r.json()
        assert data["features"].get("predictive_calibration") is expect_enabled
        assert any(
            k in data["reasons"] for k in ("analysis_keywords", "math_pattern_match", "code_pattern_match")
        )

    # Test enabled state
    flag, expect_enabled = "1", True
    sr = await _reload_for_flag(flag)
    from app.main import app  # import after reload to pick updated router module state
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r2 = await _route(client, "Explain the integral of a matrix function")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["features"].get("predictive_calibration") is expect_enabled
        assert any(x.startswith("route_calib_adj:") for x in data2["reasons"]) or "route_calib_applied" in data2["reasons"]


async def test_health_predictive_stats():
    await _reload_for_flag("1")
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/switchr/health")
        assert h.status_code == 200
        j = h.json()
        assert j["predictive_enabled"] is True
        assert "predictive_cache" in j
        assert "fallback_rate" in j
