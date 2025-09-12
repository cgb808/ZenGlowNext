"""Leonardo Audio Integration Router
Provides:
 - /leonardo/speak : Piper-backed TTS with curated voice map
 - /leonardo/think : LLM analytical response (optionally TTS)
 - /leonardo/listen : Whisper transcription (whisper.cpp CLI)
 - /leonardo/analyze-and-speak : Combined think + speak
 - /leonardo/status : Capability probe

Design notes:
 - Depends on `piper` and `whisper` executables being on PATH. If missing, endpoints return 500 (speak/listen) while /status degrades gracefully.
 - LLM backend forced via `prefer="leonardo"` (mistral 7B variant) using existing `LLMClient` unify path.
 - Uses temporary files for Piper input/output, deleted after use.
 - Avoids throwing during import if LLMClient path shifts (soft import guard).
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from app.audio.tts_core import synthesize_base64, VOICE_ALIASES  # reuse core TTS

try:  # Defensive import; if refactored later we still load router
    from app.rag.llm_client import LLMClient  # type: ignore
except Exception:  # pragma: no cover - extremely rare
    LLMClient = None  # type: ignore

router = APIRouter(prefix="/leonardo", tags=["leonardo-audio"])
log = logging.getLogger("app.leonardo.audio")


class LeonardoSpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "leonardo"  # default curated voice
    format: Optional[str] = "base64"  # base64|file
    emotion: Optional[str] = "analytical"  # semantic hint only


class LeonardoThinkRequest(BaseModel):
    query: str
    context: Optional[str] = None
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 1024
    speak_response: Optional[bool] = True


class LeonardoResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    metadata: Dict[str, Any]


VOICE_MAP = {
    "leonardo": "en_GB-northern_english_male-medium",
    "analytical": "en_US-lessac-medium",
    "teaching": "en_US-amy-medium",
    "encouraging": "en_GB-alba-medium",
}


def _ensure_binary(name: str) -> bool:
    return subprocess.run(["which", name], capture_output=True).returncode == 0


@router.post("/speak", response_model=Dict[str, Any])
async def leonardo_speak(request: LeonardoSpeakRequest):
    """Generate TTS audio (delegates to core Piper synthesis)."""
    # Map legacy leonardo voice names to VOICE_ALIASES if possible
    voice_key = request.voice or "leonardo"
    # If mapped alias doesn't exist in unified map, fallback to static VOICE_MAP
    if voice_key in VOICE_ALIASES:
        resolved = voice_key
    else:
        resolved = VOICE_MAP.get(voice_key, VOICE_MAP["leonardo"])
    b64, size, model = synthesize_base64(request.text, voice=resolved)
    return {
        "success": True,
        "audio_base64": b64,
        "voice": resolved,
        "emotion": request.emotion,
        "text_length": len(request.text),
        "audio_size": size,
        "model_path": model,
    }


@router.post("/think", response_model=LeonardoResponse)
async def leonardo_think(request: LeonardoThinkRequest):
    """Analytical LLM response optionally with TTS."""
    if LLMClient is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="LLMClient unavailable")
    try:
        analytical_prompt = (
            "You are Leonardo, an analytical AI assistant focused on deep thinking and educational excellence.\n\n"
            f"Query: {request.query}\n\n"
            + (f"Additional context: {request.context}\n\n" if request.context else "")
            + "Provide a thoughtful, well-reasoned response considering multiple perspectives and clear explanations."
        )
        llm_client = LLMClient()
        meta = llm_client.generate_with_metadata(
            prompt=analytical_prompt,
            prefer="leonardo",
            temperature=request.temperature,
            max_tokens=request.max_tokens or 1024,
        )
        text = meta.get("text", "")
        if not text:
            raise HTTPException(status_code=500, detail="Leonardo produced no text")
        audio_b64 = None
        if request.speak_response:
            try:
                speak_req = LeonardoSpeakRequest(text=text, voice="leonardo", emotion="analytical")
                speak_res = await leonardo_speak(speak_req)
                audio_b64 = speak_res.get("audio_base64")  # type: ignore[arg-type]
            except Exception as e:  # noqa: BLE001
                log.warning("leonardo.think.tts_fail %s", e)
        return LeonardoResponse(
            text=text,
            audio_base64=audio_b64,
            metadata={
                "backend": meta.get("backend"),
                "latency_ms": meta.get("total_latency_ms"),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "has_audio": audio_b64 is not None,
                "errors": meta.get("errors", []),
            },
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("leonardo.think.error")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e}")


@router.post("/listen")
async def leonardo_listen(audio_file: UploadFile = File(...)):
    """Speech-to-text using whisper.cpp CLI."""
    if not _ensure_binary("whisper"):
        raise HTTPException(status_code=500, detail="whisper binary not available")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        try:
            cmd = [
                "whisper",
                temp_audio_path,
                "--model",
                "base",
                "--output-format",
                "txt",
                "--no-timestamps",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.returncode != 0:
                log.error("whisper.fail %s", result.stderr)
                raise HTTPException(status_code=500, detail="Speech recognition failed")
            transcript = result.stdout.strip()
            return {
                "success": True,
                "transcript": transcript,
                "model": "whisper-base",
                "audio_duration": None,
                "confidence": None,
            }
        finally:
            try:
                os.unlink(temp_audio_path)
            except Exception:  # noqa: BLE001
                pass
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("leonardo.listen.error")
        raise HTTPException(status_code=500, detail=f"Speech recognition error: {e}")


@router.post("/analyze-and-speak")
async def leonardo_analyze_and_speak(request: LeonardoThinkRequest):
    """Shortcut invoking think with speak enabled."""
    request.speak_response = True
    return await leonardo_think(request)


@router.get("/status")
async def leonardo_status():
    """Report capability status without raising exceptions."""
    try:
        llm_ok = False
        backend = None
        if LLMClient is not None:
            try:
                client = LLMClient()
                meta = client.generate_with_metadata(
                    prompt="Test connectivity", prefer="leonardo", max_tokens=8
                )
                backend = meta.get("backend")
                llm_ok = backend == "leonardo"
            except Exception:  # noqa: BLE001
                pass
        tts_ok = _ensure_binary("piper")
        whisper_ok = _ensure_binary("whisper")
        status = (
            "ready" if all([llm_ok, tts_ok, whisper_ok]) else ("partial" if any([llm_ok, tts_ok, whisper_ok]) else "down")
        )
        return {
            "leonardo_model": llm_ok,
            "backend": backend,
            "tts_available": tts_ok,
            "speech_recognition": whisper_ok,
            "status": status,
            "capabilities": {
                "analytical_thinking": llm_ok,
                "text_to_speech": tts_ok,
                "speech_to_text": whisper_ok,
                "voice_interaction": llm_ok and tts_ok and whisper_ok,
            },
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "error": str(e),
            "capabilities": {
                "analytical_thinking": False,
                "text_to_speech": False,
                "speech_to_text": False,
                "voice_interaction": False,
            },
        }
