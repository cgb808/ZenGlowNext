"""
Leonardo Audio Integration Router
Handles TTS and speech recognition for Leonardo (Mistral 7B)
"""

import base64
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.rag.llm_client import LLMClient

router = APIRouter(prefix="/leonardo", tags=["leonardo-audio"])
log = logging.getLogger("app.leonardo.audio")


class LeonardoSpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "leonardo"  # Default voice for Leonardo
    format: Optional[str] = "base64"  # base64|file|wav
    emotion: Optional[str] = "analytical"  # analytical|teaching|explaining|encouraging


class LeonardoThinkRequest(BaseModel):
    query: str
    context: Optional[str] = None
    temperature: Optional[float] = 0.3  # Slightly higher for creative thinking
    max_tokens: Optional[int] = 1024  # Longer responses for analysis
    speak_response: Optional[bool] = True  # Auto-generate TTS


class LeonardoResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    metadata: Dict[str, Any]


@router.post("/speak", response_model=Dict[str, Any])
async def leonardo_speak(request: LeonardoSpeakRequest):
    """
    Generate TTS audio for Leonardo with analytical voice characteristics
    """
    try:
        # Use Piper TTS with Leonardo's voice
        voice_map = {
            "leonardo": "en_GB-northern_english_male-medium",  # Thoughtful British accent
            "analytical": "en_US-lessac-medium",  # Clear, analytical tone
            "teaching": "en_US-amy-medium",  # Warm teaching voice
            "encouraging": "en_GB-alba-medium",  # Encouraging British voice
        }

        piper_voice = voice_map.get(request.voice or "leonardo", voice_map["leonardo"])

        # Create temporary files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as text_file:
            text_file.write(request.text)
            text_file_path = text_file.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_file_path = audio_file.name

        try:
            # Run Piper TTS
            piper_cmd = [
                "piper",
                "--model",
                piper_voice,
                "--output_file",
                audio_file_path,
            ]

            with open(text_file_path, "r") as f:
                result = subprocess.run(
                    piper_cmd, stdin=f, capture_output=True, text=True, timeout=30
                )

            if result.returncode != 0:
                log.error(f"Piper TTS failed: {result.stderr}")
                raise HTTPException(
                    status_code=500, detail=f"TTS generation failed: {result.stderr}"
                )

            # Read and encode audio
            with open(audio_file_path, "rb") as f:
                audio_data = f.read()

            if request.format == "base64":
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "voice": piper_voice,
                    "emotion": request.emotion,
                    "text_length": len(request.text),
                    "audio_size": len(audio_data),
                }
            else:
                # Return file path or raw data based on format
                return {
                    "success": True,
                    "audio_file": audio_file_path,
                    "voice": piper_voice,
                    "emotion": request.emotion,
                }

        finally:
            # Cleanup temporary files
            try:
                os.unlink(text_file_path)
                os.unlink(audio_file_path)
            except:
                pass

    except Exception as e:
        log.error(f"Leonardo TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.post("/think", response_model=LeonardoResponse)
async def leonardo_think(request: LeonardoThinkRequest):
    """
    Leonardo's analytical thinking with optional TTS response
    """
    try:
        # Create analytical prompt for Leonardo
        analytical_prompt = f"""You are Leonardo, an analytical AI assistant focused on deep thinking and educational excellence.

Query: {request.query}

{f"Additional context: {request.context}" if request.context else ""}

Please provide a thoughtful, well-reasoned response that demonstrates analytical thinking. Consider multiple perspectives, provide clear explanations, and offer educational insights where appropriate."""

        # Generate response using Leonardo backend
        llm_client = LLMClient()
        response_meta = llm_client.generate_with_metadata(
            prompt=analytical_prompt,
            prefer="leonardo",  # Force Leonardo backend
            temperature=request.temperature,
            max_tokens=request.max_tokens or 1024,
        )

        response_text = response_meta.get("text", "")
        if not response_text:
            raise HTTPException(
                status_code=500, detail="Leonardo did not generate a response"
            )

        # Generate TTS if requested
        audio_base64 = None
        if request.speak_response:
            try:
                speak_request = LeonardoSpeakRequest(
                    text=response_text, voice="leonardo", emotion="analytical"
                )
                tts_result = await leonardo_speak(speak_request)
                audio_base64 = tts_result.get("audio_base64")
            except Exception as e:
                log.warning(f"TTS generation failed for Leonardo response: {e}")

        return LeonardoResponse(
            text=response_text,
            audio_base64=audio_base64,
            metadata={
                "backend": response_meta.get("backend"),
                "latency_ms": response_meta.get("total_latency_ms"),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "has_audio": audio_base64 is not None,
                "errors": response_meta.get("errors", []),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Leonardo think error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.post("/listen")
async def leonardo_listen(audio_file: UploadFile = File(...)):
    """
    Speech-to-text for Leonardo using Whisper
    """
    try:
        # Save uploaded audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        try:
            # Use whisper.cpp for transcription
            whisper_cmd = [
                "whisper",
                temp_audio_path,
                "--model",
                "base",
                "--output-format",
                "txt",
                "--no-timestamps",
            ]

            result = subprocess.run(
                whisper_cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                log.error(f"Whisper transcription failed: {result.stderr}")
                raise HTTPException(status_code=500, detail="Speech recognition failed")

            transcript = result.stdout.strip()

            return {
                "success": True,
                "transcript": transcript,
                "model": "whisper-base",
                "audio_duration": None,  # Could calculate this if needed
                "confidence": None,  # Whisper doesn't provide confidence scores
            }

        finally:
            # Cleanup temporary file
            try:
                os.unlink(temp_audio_path)
            except:
                pass

    except Exception as e:
        log.error(f"Leonardo speech recognition error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Speech recognition error: {str(e)}"
        )


@router.post("/analyze-and-speak")
async def leonardo_analyze_and_speak(request: LeonardoThinkRequest):
    """
    Combined endpoint: Leonardo analyzes the query and speaks the response
    """
    # Force speaking for this endpoint
    request.speak_response = True
    return await leonardo_think(request)


@router.get("/status")
async def leonardo_status():
    """
    Check Leonardo's availability and audio capabilities
    """
    try:
        # Test Leonardo backend
        llm_client = LLMClient()
        test_response = llm_client.generate_with_metadata(
            prompt="Test connectivity", prefer="leonardo", max_tokens=10
        )

        leonardo_available = test_response.get("backend") == "leonardo"

        # Test TTS availability
        tts_available = (
            subprocess.run(["which", "piper"], capture_output=True).returncode == 0
        )

        # Test Whisper availability
        whisper_available = (
            subprocess.run(["which", "whisper"], capture_output=True).returncode == 0
        )

        return {
            "leonardo_model": leonardo_available,
            "tts_available": tts_available,
            "speech_recognition": whisper_available,
            "status": (
                "ready"
                if all([leonardo_available, tts_available, whisper_available])
                else "partial"
            ),
            "capabilities": {
                "analytical_thinking": leonardo_available,
                "text_to_speech": tts_available,
                "speech_to_text": whisper_available,
                "voice_interaction": leonardo_available
                and tts_available
                and whisper_available,
            },
        }

    except Exception as e:
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
"""Leonardo audio router stub.

Provides a placeholder endpoint so imports in `app.main` succeed. Replace with
real implementation when Leonardo audio features are defined.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/leonardo")


@router.get("/ping")
async def leonardo_ping() -> dict[str, str]:  # pragma: no cover - trivial
    return {"ok": "true"}
