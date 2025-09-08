import base64
import os
import subprocess
import tempfile

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PIPER_BIN = os.getenv("PIPER_BIN", "vendor/piper/piper")
PIPER_MODEL = os.getenv("PIPER_MODEL", "models/piper/en_US-amy-low.onnx")

# Optional additional model paths (user can export these in .env)
PIPER_JARVIS_MODEL = os.getenv("PIPER_JARVIS_MODEL", "models/piper/en_GB-alan-low.onnx")
PIPER_ALAN_MODEL = os.getenv("PIPER_ALAN_MODEL", PIPER_JARVIS_MODEL)
PIPER_SOUTHERN_MALE_MODEL = os.getenv(
    "PIPER_SOUTHERN_MALE_MODEL", "models/piper/en_GB-southern_english_male-low.onnx"
)

VOICE_ALIASES = {
    # Treat these short names as aliases for clarity in the UI.
    "jarvis": PIPER_JARVIS_MODEL,
    "alan": PIPER_ALAN_MODEL,
    "southern_male": PIPER_SOUTHERN_MALE_MODEL,
    "amy": PIPER_MODEL,
}

router = APIRouter(prefix="/audio", tags=["audio"])


class TTSPayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str | None = Field(
        None,
        description="Voice alias (jarvis, alan, southern_male, amy) or explicit model path to .onnx",
    )
    speed: float | None = Field(None, ge=0.5, le=2.0)
    format: str | None = Field(None, description="Return format: base64|wav")


@router.post("/tts")
def tts(payload: TTSPayload):
    if not os.path.exists(PIPER_BIN):
        raise HTTPException(500, detail="piper binary not found (set PIPER_BIN env)")
    # Resolve voice alias -> model path (only if no path separator present)
    if payload.voice:
        if os.path.sep not in payload.voice and payload.voice in VOICE_ALIASES:
            model_path = VOICE_ALIASES[payload.voice]
        else:
            model_path = payload.voice
    else:
        model_path = PIPER_MODEL
    if not os.path.exists(model_path):
        raise HTTPException(500, detail=f"piper model not found: {model_path}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_f:
        out_path = out_f.name
    cmd = [PIPER_BIN, "--model", model_path, "--output_file", out_path]
    if payload.speed and abs(payload.speed - 1.0) > 1e-6:
        cmd += ["--length_scale", f"{1.0/payload.speed:.3f}"]
    try:
        proc = subprocess.run(
            cmd, input=payload.text.encode("utf-8"), capture_output=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise HTTPException(504, detail="piper timeout")
    if proc.returncode != 0:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise HTTPException(
            500, detail=f"piper failed: {proc.stderr.decode('utf-8')[-300:]}"
        )
    try:
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)
    if payload.format and payload.format not in ("wav", "base64"):
        raise HTTPException(400, detail="invalid format (expected 'wav' or 'base64')")
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    # Standardize key to audio_base64; keep legacy audio_b64 for backward compatibility
    return {
        "audio_base64": b64,
        "audio_b64": b64,
        "mime": "audio/wav",
        "bytes": len(audio_bytes),
        "model_path": model_path,
    }


@router.get("/tts/voices")
def list_voices():
    """Return the configured voice aliases and resolved model paths."""
    return {k: v for k, v in VOICE_ALIASES.items()}
