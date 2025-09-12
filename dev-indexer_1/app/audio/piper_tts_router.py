"""Piper TTS Router (scoped under /audio/piper)

Separates Piper binary-backed synthesis from any other TTS providers.

Environment Variables:
  PIPER_BIN  (default vendor/piper/piper)
  PIPER_MODEL (default models/piper/en_US-amy-low.onnx)
  PIPER_JARVIS_MODEL
  PIPER_ALAN_MODEL
  PIPER_SOUTHERN_MALE_MODEL

Endpoints:
  POST /audio/piper/tts          -> synthesize text
  GET  /audio/piper/tts/voices   -> list alias -> model path mapping
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.audio.tts_core import VOICE_ALIASES, synthesize_base64, PIPER_BIN

router = APIRouter(prefix="/audio/piper", tags=["audio-piper"])


class PiperTTSPayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: Optional[str] = Field(
        None,
        description="Voice alias (jarvis, alan, southern_male, amy) or explicit model path to .onnx",
    )
    speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    format: Optional[str] = Field(None, description="Return format: base64|wav")


@router.post("/tts")
def piper_tts(payload: PiperTTSPayload):  # pragma: no cover - thin IO wrapper
    if not os.path.exists(PIPER_BIN):
        raise HTTPException(500, detail="piper binary not found (set PIPER_BIN env)")
    b64, byte_len, model = synthesize_base64(
        payload.text, voice=payload.voice, speed=payload.speed
    )
    return {
        "audio_base64": b64,
        "audio_b64": b64,
        "mime": "audio/wav",
        "bytes": byte_len,
        "model_path": model,
    }


@router.get("/tts/voices")
def piper_list_voices():
    return {k: v for k, v in VOICE_ALIASES.items()}
