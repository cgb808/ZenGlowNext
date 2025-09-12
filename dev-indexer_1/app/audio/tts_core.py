"""Core Piper TTS service (deduplicated logic).

Routers (`/audio/tts`, `/audio/piper/tts`, future Jarvis/Leonardo speak) call
`synthesize_base64` instead of re-implementing subprocess + temp file handling.

Design:
 - Accepts voice alias OR explicit model path / model id.
 - Only asserts filesystem existence when the value looks like a path
   (contains a path separator or endswith .onnx). This preserves prior behavior
   of accepting plain model identifiers used by some packaged voices.
 - Speed param mapped to Piper `--length_scale` (inverse proportional).
 - Returns base64 audio plus model identifier used.
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from typing import Optional, Tuple

from fastapi import HTTPException

# Environment + alias resolution -------------------------------------------------
PIPER_BIN = os.getenv("PIPER_BIN", "vendor/piper/piper")
PIPER_MODEL = os.getenv("PIPER_MODEL", "models/piper/en_US-amy-low.onnx")
PIPER_JARVIS_MODEL = os.getenv("PIPER_JARVIS_MODEL", "models/piper/en_GB-alan-low.onnx")
PIPER_ALAN_MODEL = os.getenv("PIPER_ALAN_MODEL", PIPER_JARVIS_MODEL)
PIPER_SOUTHERN_MALE_MODEL = os.getenv(
    "PIPER_SOUTHERN_MALE_MODEL", "models/piper/en_GB-southern_english_male-low.onnx"
)

# Unified alias map (extendable)
VOICE_ALIASES = {
    "jarvis": PIPER_JARVIS_MODEL,
    "alan": PIPER_ALAN_MODEL,
    "southern_male": PIPER_SOUTHERN_MALE_MODEL,
    "amy": PIPER_MODEL,
}


def _resolve_model(voice: Optional[str]) -> str:
    if not voice:
        return PIPER_MODEL
    # Alias (no path sep & known)
    if os.path.sep not in voice and voice in VOICE_ALIASES:
        return VOICE_ALIASES[voice]
    return voice


def _is_filesystem_model(model: str) -> bool:
    return os.path.sep in model or model.endswith(".onnx")


def synthesize_base64(
    text: str,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
    timeout: int = 120,
) -> Tuple[str, int, str]:
    """Run Piper TTS and return (base64_audio, num_bytes, model_identifier).

    Raises HTTPException on failure to align with existing router contracts.
    """
    if not os.path.exists(PIPER_BIN):  # binary required
        raise HTTPException(500, detail="piper binary not found (set PIPER_BIN env)")
    model = _resolve_model(voice)
    if _is_filesystem_model(model) and not os.path.exists(model):
        raise HTTPException(500, detail=f"piper model not found: {model}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_f:
        out_path = out_f.name
    cmd = [PIPER_BIN, "--model", model, "--output_file", out_path]
    if speed and abs(speed - 1.0) > 1e-6:
        cmd += ["--length_scale", f"{1.0 / speed:.3f}"]
    try:
        proc = subprocess.run(
            cmd, input=text.encode("utf-8"), capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise HTTPException(504, detail="piper timeout")
    if proc.returncode != 0:
        if os.path.exists(out_path):
            os.unlink(out_path)
        stderr_tail = proc.stderr.decode("utf-8", errors="ignore")[-300:]
        raise HTTPException(500, detail=f"piper failed: {stderr_tail}")
    try:
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    return b64, len(audio_bytes), model
