from app.core.metrics_facade import counter, observe, timer, snapshot


def test_counter_and_snapshot():
    counter("requests_total")
    counter("requests_total", inc=2)
    data = snapshot()
    # Flatten keys
    counters = data["counters"]
    # Key may include label dict; just find one that startswith name
    assert any(k.startswith("requests_total|") for k in counters.keys())
    total = sum(v for k, v in counters.items() if k.startswith("requests_total|"))
    assert total == 3


def test_observe_and_timer():
    observe("latency_ms", 5.0)
    with timer("latency_ms") as t:
        _ = t  # no-op work
    data = snapshot()
    obs = [vals for k, vals in data["observations"].items() if k.startswith("latency_ms|")]
    assert obs, "latency observations missing"
    flat = [v for sub in obs for v in sub]
    assert any(v >= 0.0 for v in flat)
