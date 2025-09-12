"""Legacy Piper TTS router (/audio/tts).

Refactored to delegate to `app.audio.tts_core` shared implementation. New
namespaced implementation lives at `/audio/piper/tts`. This router remains for
backward compatibility and will emit a deprecation header in responses.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.audio.tts_core import (
    VOICE_ALIASES,  # reuse alias map
    synthesize_base64,
)

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
def tts(payload: TTSPayload, response: Response):
    b64, byte_len, model = synthesize_base64(
        payload.text, voice=payload.voice, speed=payload.speed
    )
    # Deprecation signal
    response.headers["X-Deprecation"] = "Use /audio/piper/tts"
    return {
        "audio_base64": b64,
        "audio_b64": b64,
        "mime": "audio/wav",
        "bytes": byte_len,
        "model_path": model,
    }


@router.get("/tts/voices")
def list_voices():  # pragma: no cover - trivial mapping
    return {k: v for k, v in VOICE_ALIASES.items()}
