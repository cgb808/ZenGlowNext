"""Global pytest configuration & lightweight mode defaults.

Lightweight mode (default) tries to avoid importing / initializing heavy
audio or model components that were contributing to SSH session instability
by exhausting memory or triggering long downloads during test collection.

Override any of these by exporting the corresponding env var with value "0".
Examples:
	SKIP_INTEGRATION_TESTS=0 SKIP_WAKE_TESTS=0 pytest -q
"""

import os
import sys
import threading
import time

# Core env so app imports do not fail fast
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("APP_TEST_MODE", "1")
os.environ.setdefault("SKIP_DB", "1")
os.environ.setdefault("ALLOW_EMBED_FALLBACK", "true")

# Lightweight-mode skip toggles (can be unset by user to run full suite)
os.environ.setdefault("SKIP_AUDIO_TESTS", "1")  # skips piper / whisper heavy paths
os.environ.setdefault("SKIP_WAKE_TESTS", "1")  # skips wake word async loop tests
os.environ.setdefault(
    "SKIP_INTEGRATION_TESTS", "1"
)  # skips API TestClient integration hits
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_MAX_THREADS", "1")
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# ---------------- Heartbeat / Progress Ticker -----------------
_hb_stop = threading.Event()


def _heartbeat():  # pragma: no cover - infrastructure utility
    interval = float(os.getenv("TEST_HEARTBEAT_INTERVAL", "15"))
    counter = 0
    while not _hb_stop.is_set():
        counter += 1
        # Write directly to stderr to bypass normal stdout capture; tee-sys will mirror
        sys.stderr.write(
            f"[test-heartbeat #{counter}] alive {time.strftime('%H:%M:%S')}\n"
        )
        sys.stderr.flush()
        _hb_stop.wait(interval)


def pytest_sessionstart(session):  # noqa: D401
    if os.getenv("DISABLE_TEST_HEARTBEAT") == "1":
        return
    t = threading.Thread(target=_heartbeat, name="pytest-heartbeat", daemon=True)
    t.start()


def pytest_sessionfinish(session, exitstatus):  # noqa: D401
    _hb_stop.set()
