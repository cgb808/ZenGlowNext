"""Simple transcription stub router used when full audio stack is skipped.

Provides a placeholder /audio/transcribe endpoint returning a static message.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/audio", tags=["audio-simple"])


@router.post("/transcribe")  # pragma: no cover - trivial stub
async def transcribe_stub():
	return {"transcript": None, "detail": "full transcription stack disabled"}

