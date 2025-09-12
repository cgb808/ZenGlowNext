"""Tests for predictive cache metrics instrumentation.

Verifies that repeated predictions produce hit/miss counters and that
cache size observation is recorded. We only exercise the existing
`route_calibration` model via the public controller API.
"""
from __future__ import annotations

import os

from app.predictive.controller import get_predictive_controller
from app.core import metrics_facade


def test_predictive_cache_metrics():
    os.environ["ENABLE_ROUTE_CALIB"] = "1"  # ensure model loaded (guarded upstream)
    ctrl = get_predictive_controller()

    context = {"backend_speed_ms": 12, "tokens": 42, "duration_ms": 1000}

    # First call -> miss
    out1 = ctrl.predict("route_calibration", context)
    assert out1 is not None

    # Second call same context -> hit
    out2 = ctrl.predict("route_calibration", context)
    assert out2 is not None

    snap = metrics_facade.snapshot()
    counters = snap["counters"]
    observations = snap["observations"]

    # Validate counters
    # Keys have format name|{labels}
    hit_keys = [k for k in counters if k.startswith("predictive_cache_hits|")]
    miss_keys = [k for k in counters if k.startswith("predictive_cache_misses|")]
    assert hit_keys, "expected at least one hit counter key"
    assert miss_keys, "expected at least one miss counter key"
    # Sum values to avoid depending on exact label ordering
    total_hits = sum(counters[k] for k in hit_keys)
    total_misses = sum(counters[k] for k in miss_keys)
    assert total_hits >= 1
    assert total_misses >= 1

    size_obs_keys = [k for k in observations if k.startswith("predictive_cache_size|")]
    assert size_obs_keys, "expected size observation entries"
    # At least one recorded size value and it should be >= 1
    recorded_sizes = [v for k in size_obs_keys for v in observations[k]]
    assert any(s >= 1 for s in recorded_sizes)
