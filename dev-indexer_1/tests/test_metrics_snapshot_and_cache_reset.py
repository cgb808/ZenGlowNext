"""Tests for metrics snapshot endpoint and predictive cache reset helper."""
from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app.main import app  # FastAPI app
from app.predictive.controller import get_predictive_controller, reset_predictive_cache
from app.core import metrics_facade


def test_metrics_snapshot_endpoint_and_predictive_reset():
    os.environ["ENABLE_ROUTE_CALIB"] = "1"
    client = TestClient(app)

    # Warm predictive cache with one miss + one hit
    ctrl = get_predictive_controller()
    ctx = {"backend_speed_ms": 5, "tokens": 10, "duration_ms": 500}
    ctrl.predict("route_calibration", ctx)
    ctrl.predict("route_calibration", ctx)

    r = client.get("/metrics/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "counters" in data and "observations" in data

    # Confirm predictive counters present
    counter_keys = data["counters"].keys()
    assert any(k.startswith("predictive_cache_hits|") for k in counter_keys)
    assert any(k.startswith("predictive_cache_misses|") for k in counter_keys)

    # Reset predictive cache
    reset_predictive_cache()
    stats_after = ctrl.stats()
    assert stats_after["cache_hits"] == 0
    assert stats_after["cache_misses"] == 0
    assert stats_after["cache_entries"] == 0

    # Additional call after reset should repopulate
    ctrl.predict("route_calibration", ctx)
    stats_repop = ctrl.stats()
    assert stats_repop["cache_misses"] == 1
    assert stats_repop["cache_entries"] == 1
