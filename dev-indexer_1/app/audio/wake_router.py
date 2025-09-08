import queue
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

try:
    from openwakeword.model import Model as WakeModel  # type: ignore

    _wake_available = True
except Exception:
    _wake_available = False
    WakeModel = None  # type: ignore

router = APIRouter(prefix="/wake", tags=["wake"])


class WakeStatus(BaseModel):
    enabled: bool
    model: Optional[str]
    detected: bool
    backend_active: bool


_state = {
    "enabled": False,
    "detected": False,
    "model_name": "hey_jarvis",  # default included small model name (example)
}

_audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=32)
_worker_thread: Optional[threading.Thread] = None
_model: Any = None  # lazy loaded


def _worker():  # pragma: no cover - runtime loop
    global _model
    if not _wake_available:
        return
    # Lazy create model (default uses built-in models dir under user cache)
    if _model is None:
        try:
            if WakeModel is None:
                _state["enabled"] = False
                return
            _model = WakeModel()  # loads default set
        except Exception:
            _state["enabled"] = False
            return
    last_detect = 0.0
    while _state["enabled"]:
        try:
            chunk = _audio_q.get(timeout=0.25)
        except queue.Empty:
            continue
        try:
            if _model is None:
                continue
            scores = _model.predict(chunk)
        except Exception:
            continue
        # scores is dict model_name->prob
        for name, score in scores.items():
            if name == _state["model_name"] and score >= 0.6:  # threshold
                now = time.time()
                if now - last_detect > 2.0:  # cooldown
                    _state["detected"] = True
                    last_detect = now
        # Slight yield
        time.sleep(0.005)
    # loop exit


@router.get("/status", response_model=WakeStatus)
def wake_status():
    return WakeStatus(
        enabled=_state["enabled"],
        model=_state["model_name"],
        detected=_state["detected"],
        backend_active=_worker_thread is not None and _worker_thread.is_alive(),
    )


class WakeEnableRequest(BaseModel):
    enabled: bool
    model: Optional[str] = None


@router.post("/enable", response_model=WakeStatus)
def wake_enable(req: WakeEnableRequest):
    # Toggle
    changed = False
    if req.model:
        _state["model_name"] = req.model
    if req.enabled and not _state["enabled"]:
        _state["enabled"] = True
        changed = True
    elif (not req.enabled) and _state["enabled"]:
        _state["enabled"] = False
        changed = True
    if changed and _state["enabled"] and _wake_available:
        global _worker_thread
        _state["detected"] = False
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()
    return wake_status()


class WakeAudioChunk(BaseModel):
    pcm16: bytes  # raw little-endian 16-bit mono 16k


@router.post("/push", response_model=WakeStatus)
def wake_push(chunk: WakeAudioChunk):
    if not _state["enabled"]:
        return wake_status()
    if not _wake_available:
        return wake_status()
    try:
        _audio_q.put_nowait(chunk.pcm16)
    except queue.Full:
        pass
    return wake_status()


@router.post("/clear", response_model=WakeStatus)
def wake_clear():
    _state["detected"] = False
    return wake_status()
