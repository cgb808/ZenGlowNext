"""Audio device discovery endpoints (microphones & output devices).

Uses sounddevice (preferred) or PyAudio fallback to enumerate input/output devices.
Designed for local dev / diagnostics; in containerized deployments host device mapping may be limited.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/audio", tags=["audio"])  # shares namespace with other audio routes


def _list_with_sounddevice() -> Dict[str, Any]:
    import sounddevice as sd  # type: ignore
    devices = sd.query_devices()
    inputs = []
    outputs = []
    for idx, d in enumerate(devices):
        entry = {
            "index": idx,
            "name": d.get("name"),
            "max_input_channels": d.get("max_input_channels"),
            "max_output_channels": d.get("max_output_channels"),
            "default_samplerate": d.get("default_samplerate"),
        }
        if d.get("max_input_channels", 0) > 0:
            inputs.append(entry)
        if d.get("max_output_channels", 0) > 0:
            outputs.append(entry)
    defaults = {}
    try:
        defaults = sd.default.device  # (input, output)
    except Exception:
        pass
    return {"backend": "sounddevice", "inputs": inputs, "outputs": outputs, "default": defaults}


def _list_with_pyaudio() -> Dict[str, Any]:
    import pyaudio  # type: ignore
    pa = pyaudio.PyAudio()
    inputs = []
    outputs = []
    try:
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            entry = {
                "index": idx,
                "name": info.get("name"),
                "max_input_channels": info.get("maxInputChannels"),
                "max_output_channels": info.get("maxOutputChannels"),
                "default_samplerate": info.get("defaultSampleRate"),
            }
            if entry["max_input_channels"] > 0:
                inputs.append(entry)
            if entry["max_output_channels"] > 0:
                outputs.append(entry)
        return {"backend": "pyaudio", "inputs": inputs, "outputs": outputs}
    finally:
        pa.terminate()


@router.get("/devices")
def list_devices():
    """Enumerate available audio input/output devices.

    Tries sounddevice first, falls back to PyAudio. Raises 500 if neither works.
    """
    errors: List[str] = []
    for func in (_list_with_sounddevice, _list_with_pyaudio):
        try:
            return func()
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    raise HTTPException(status_code=500, detail={"error": "no audio backend available", "attempts": errors})
