"""Lightweight audio diagnostics endpoints.

Endpoints (guarded by SOUND_DIAG_ENABLE env flag in main app):
  GET /audio/diag/ping          -> basic liveness
  GET /audio/diag/devices       -> list available input/output devices (best-effort)
  POST /audio/diag/tone         -> generate a short sine tone WAV (base64)
  POST /audio/diag/mic-sample   -> (stub) capture brief mic input if sounddevice present

This avoids pulling heavy deps by importing optional libs lazily.
"""

from __future__ import annotations

import base64
import io
import math
import wave
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/audio/diag", tags=["audio-diagnostics"])


def _try_import_sounddevice():  # returns module or None
    try:
        import sounddevice as sd  # type: ignore

        return sd
    except Exception:
        return None


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    return {"ok": True, "feature": "audio-diagnostics"}


@router.get("/devices")
async def list_devices() -> Dict[str, Any]:
    sd = _try_import_sounddevice()
    if not sd:
        return {"available": False, "reason": "sounddevice not installed"}
    try:
        devices = sd.query_devices()  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover - hardware specific
        return {"available": False, "error": str(e)}
    # Trim noisy fields
    simplified: List[Dict[str, Any]] = []
    for idx, d in enumerate(devices):  # type: ignore[assignment]
        simplified.append(
            {
                "index": idx,
                "name": d.get("name"),
                "max_input_channels": d.get("max_input_channels"),
                "max_output_channels": d.get("max_output_channels"),
                "default_samplerate": d.get("default_samplerate"),
            }
        )
    return {"available": True, "devices": simplified}


@router.post("/tone")
async def generate_tone(
    seconds: float = 0.5, freq: float = 440.0, sample_rate: int = 16000
) -> Dict[str, Any]:
    if seconds <= 0 or seconds > 5:
        raise HTTPException(status_code=400, detail="seconds must be between 0 and 5")
    if sample_rate not in (8000, 16000, 22050, 24000, 44100, 48000):
        raise HTTPException(status_code=400, detail="unsupported sample_rate")
    total_samples = int(seconds * sample_rate)
    amplitude = 0.3
    frames = bytearray()
    for n in range(total_samples):
        sample = amplitude * math.sin(2 * math.pi * freq * (n / sample_rate))
        # 16-bit PCM
        val = int(max(min(sample, 0.9999), -0.9999) * 32767)
        frames += val.to_bytes(2, byteorder="little", signed=True)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(frames)
    wav_bytes = buf.getvalue()
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    return {"wav_base64": b64, "seconds": seconds, "freq": freq, "sample_rate": sample_rate}


@router.post("/mic-sample")
async def mic_sample(seconds: float = 1.5, sample_rate: int = 16000) -> Dict[str, Any]:
    sd = _try_import_sounddevice()
    if not sd:
        return {"captured": False, "reason": "sounddevice not installed"}
    if seconds <= 0 or seconds > 10:
        raise HTTPException(status_code=400, detail="seconds must be between 0 and 10")
    try:
        import numpy as np  # type: ignore

        frames = int(seconds * sample_rate)
        data = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")  # type: ignore[attr-defined]
        sd.wait()  # type: ignore[attr-defined]
        # Convert to PCM16
        pcm = (np.clip(data[:, 0], -1.0, 1.0) * 32767).astype("int16").tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"captured": True, "seconds": seconds, "sample_rate": sample_rate, "wav_base64": b64}
    except Exception as e:  # pragma: no cover - hardware/env specific
        return {"captured": False, "error": str(e)}
