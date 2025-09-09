"""Tests for wake word router functionality with a mocked lightweight model.

We patch the wake_router's model constructor to avoid loading the real openwakeword models
and force predictable detection by returning a score > threshold for the configured model_name.

Detection loop is asynchronous in a background thread; tests poll /wake/status until detected or timeout.
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

# Ensure required env vars so app.main doesn't fail validation
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

SKIP_WAKE = os.getenv("SKIP_WAKE_TESTS") == "1"

if not SKIP_WAKE:
    from app.audio import wake_router
    from app.main import app  # ensures router registered
else:
    app = None  # type: ignore
    wake_router = None  # type: ignore

client = TestClient(app) if not SKIP_WAKE else None  # type: ignore

pytestmark = pytest.mark.skipif(SKIP_WAKE, reason="SKIP_WAKE_TESTS=1")


class FakeWakeModel:
    def predict(self, chunk: bytes):  # chunk is raw bytes
        # Always return strong score for current model_name to trigger detection
        return {wake_router._state["model_name"]: 0.95}


def _force_mock_model():
    # Enable availability and replace constructor
    wake_router._wake_available = True  # type: ignore
    wake_router.WakeModel = lambda: FakeWakeModel()  # type: ignore
    # Reset model so worker lazy-loads fake
    wake_router._model = None  # type: ignore


def _wait_for(predicate, timeout=2.0):
    start = time.time()
    while time.time() - start < timeout:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_wake_status_initial_disabled():
    resp = client.get("/wake/status")
    assert resp.status_code == 200
    js = resp.json()
    assert js["enabled"] is False
    assert js["detected"] is False


def test_wake_enable_and_detect():
    _force_mock_model()
    # Enable wake
    resp = client.post("/wake/enable", json={"enabled": True, "model": "hey_jarvis"})
    assert resp.status_code == 200
    js = resp.json()
    assert js["enabled"] is True
    # Push a dummy PCM16 chunk (2 bytes silence) base64 => 'AAA=' but minimal length helps loop
    resp2 = client.post("/wake/push", json={"pcm16": "AAAA"})
    assert resp2.status_code == 200
    # Poll until detected flips True
    assert _wait_for(
        lambda: client.get("/wake/status").json()["detected"] is True
    ), "wake word not detected in time"
    # Clear detection
    resp3 = client.post("/wake/clear")
    assert resp3.status_code == 200
    assert resp3.json()["detected"] is False


def test_wake_disable():
    # Disable
    resp = client.post("/wake/enable", json={"enabled": False})
    assert resp.status_code == 200
    js = resp.json()
    assert js["enabled"] is False
    # Pushing while disabled should not set detected
    client.post("/wake/push", json={"pcm16": "AAAA"})
    time.sleep(0.1)
    assert client.get("/wake/status").json()["detected"] is False
