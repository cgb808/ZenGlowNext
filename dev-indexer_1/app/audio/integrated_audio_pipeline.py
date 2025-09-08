
#!/usr/bin/env python3
"""
Integration layer for tiny tool controller with existing TTS/STT infrastructure.
This bridges the gap between WhisperCPP, tiny tool controller, Phi-3 specialists, and Piper TTS.
"""

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ToolClassification:
    """Structured tool classification from tiny model."""

    primary_category: str
    tools_needed: List[str]
    specialist_required: str
    confidence: float
    voice_preference: str
    parameters: Dict[str, Any]


@dataclass
class AudioProcessingResult:
    """Result from complete audio processing pipeline."""

    transcription: str
    tool_classification: ToolClassification
    specialist_response: str
    tool_outputs: Dict[str, Any]
    audio_output: bytes
    processing_time_ms: int


class WhisperCPPTranscriber:
    """Integration with existing WhisperCPP setup."""

    def __init__(self):
        self.whisper_base = os.getenv("WHISPER_CPP_DIR", "vendor/whisper.cpp")
        self.whisper_model = os.getenv("WHISPER_MODEL", "small.en")
        self.model_path = os.path.join(
            self.whisper_base, "models", f"ggml-{self.whisper_model}.bin"
        )
        self.binary_path = os.path.join(self.whisper_base, "main")

        # Verify setup
        if not os.path.exists(self.binary_path):
            # Minimal stub: avoid crashing on import if binary missing.
            # Real implementation should raise or download model.
            logger.warning("whisper.cpp binary not found at %s", self.binary_path)
            # Keep instance usable in dev by flagging unavailable state
            self.unavailable = True
        else:
            self.unavailable = False