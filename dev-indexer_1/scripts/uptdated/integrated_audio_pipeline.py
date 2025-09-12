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
            raise RuntimeError("whisper.cpp binary not found. Run setup script.")
        if not os.path.exists(self.model_path):
            raise RuntimeError(f"Whisper model not found: {self.model_path}")

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio using WhisperCPP."""
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Run WhisperCPP
            cmd = [self.binary_path, "-m", self.model_path, "-f", tmp_path, "-otxt"]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"WhisperCPP failed: {stderr.decode()}")

            # Extract transcript (WhisperCPP outputs to .txt file)
            txt_path = tmp_path.replace(".wav", ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r") as f:
                    transcript = f.read().strip()
                os.unlink(txt_path)
            else:
                transcript = stdout.decode().strip()

            return transcript

        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TinyToolController:
    """Ultra-fast tool classification using quantized tiny model."""

    def __init__(self, model_path: str = "models/tiny_tool_controller_q4_k_m.gguf"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load quantized tiny model for inference."""
        try:
            # Try to import llama-cpp-python
            from llama_cpp import Llama

            self.model = Llama(
                model_path=self.model_path,
                n_ctx=512,
                n_threads=4,
                verbose=False,
                use_mmap=True,
                use_mlock=False,
            )
            logger.info(f"Loaded tiny tool controller: {self.model_path}")

        except ImportError:
            logger.error(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load tiny model: {e}")
            # Fallback to rule-based classification
            logger.warning("Using fallback rule-based classification")
            self.model = None

    async def classify_tools(self, user_input: str) -> ToolClassification:
        """Classify user input and determine tool requirements."""
        if self.model is not None:
            return await self._model_classify(user_input)
        else:
            return self._fallback_classify(user_input)

    async def _model_classify(self, user_input: str) -> ToolClassification:
        """Use tiny model for classification."""
        prompt = f"""<|system|>You are a lightning-fast tool classifier. Analyze the user input and output the tool classification in JSON format.<|end|>
<|user|>{user_input}<|end|>
<|assistant|>"""

        # Run inference
        response = self.model(prompt, max_tokens=200, temperature=0.1, stop=["<|end|>"])

        try:
            # Parse JSON response
            response_text = response["choices"][0]["text"].strip()
            classification_data = json.loads(response_text)

            return ToolClassification(
                primary_category=classification_data["primary_category"],
                tools_needed=classification_data["tools_needed"],
                specialist_required=classification_data["specialist_required"],
                confidence=classification_data["confidence"],
                voice_preference=classification_data["voice_preference"],
                parameters=classification_data.get("parameters", {}),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse model output: {e}. Using fallback.")
            return self._fallback_classify(user_input)

    def _fallback_classify(self, user_input: str) -> ToolClassification:
        """Fallback rule-based classification."""
        user_lower = user_input.lower()

        # Mathematical keywords
        if any(
            word in user_lower
            for word in ["solve", "calculate", "graph", "equation", "math"]
        ):
            return ToolClassification(
                primary_category="MATHEMATICAL",
                tools_needed=["calculator", "latex_renderer"],
                specialist_required="phi3_mathematics_tutor",
                confidence=0.85,
                voice_preference="jarvis",
                parameters={},
            )

        # Audio control keywords
        elif any(
            word in user_lower for word in ["wait", "pause", "stop", "louder", "voice"]
        ):
            return ToolClassification(
                primary_category="AUDIO",
                tools_needed=(
                    ["audio_pause"] if "pause" in user_lower else ["tts_speak"]
                ),
                specialist_required="phi3_conversation_handler",
                confidence=0.90,
                voice_preference="amy",
                parameters={
                    "action_type": "pause" if "pause" in user_lower else "general"
                },
            )

        # Visual keywords
        elif any(word in user_lower for word in ["show", "draw", "diagram", "chart"]):
            return ToolClassification(
                primary_category="VISUAL",
                tools_needed=["diagram_create"],
                specialist_required="phi3_visual_explainer",
                confidence=0.88,
                voice_preference="alan",
                parameters={"visual_type": "diagram"},
            )

        # Search keywords
        elif any(
            word in user_lower for word in ["what is", "tell me", "find", "search"]
        ):
            return ToolClassification(
                primary_category="SEARCH",
                tools_needed=["rag_search"],
                specialist_required="phi3_knowledge_retriever",
                confidence=0.82,
                voice_preference="jarvis",
                parameters={"search_type": "knowledge"},
            )

        # Default to mathematical
        else:
            return ToolClassification(
                primary_category="MATHEMATICAL",
                tools_needed=["calculator"],
                specialist_required="phi3_mathematics_tutor",
                confidence=0.70,
                voice_preference="jarvis",
                parameters={},
            )


class Phi3SpecialistOrchestrator:
    """Manages different Phi-3 specialist models."""

    def __init__(self):
        self.specialists = {
            "phi3_mathematics_tutor": self._load_math_specialist(),
            "phi3_conversation_handler": self._load_conversation_specialist(),
            "phi3_visual_explainer": self._load_visual_specialist(),
            "phi3_knowledge_retriever": self._load_knowledge_specialist(),
            "phi3_workflow_orchestrator": self._load_workflow_specialist(),
        }

    def _load_math_specialist(self):
        """Load mathematics tutoring specialist (trained on our 846 Socratic + 500 methodology examples)."""
        # This would load the actual fine-tuned Phi-3 model
        # For now, return a mock implementation
        return MockPhi3Specialist(
            "mathematics", "I'm your math tutor, trained on Socratic questioning."
        )

    def _load_conversation_specialist(self):
        """Load conversation handling specialist (trained on our 71 interruption examples)."""
        return MockPhi3Specialist(
            "conversation", "I handle graceful conversation flow and interruptions."
        )

    def _load_visual_specialist(self):
        """Load visual explanation specialist."""
        return MockPhi3Specialist(
            "visual", "I create diagrams and visual explanations."
        )

    def _load_knowledge_specialist(self):
        """Load knowledge retrieval specialist."""
        return MockPhi3Specialist(
            "knowledge", "I search and synthesize knowledge from your RAG system."
        )

    def _load_workflow_specialist(self):
        """Load workflow orchestration specialist."""
        return MockPhi3Specialist(
            "workflow", "I manage multi-step processes and workflows."
        )

    async def get_response(
        self,
        specialist_name: str,
        user_input: str,
        tool_context: ToolClassification,
        rag_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get response from appropriate specialist."""
        specialist = self.specialists.get(specialist_name)
        if not specialist:
            raise ValueError(f"Unknown specialist: {specialist_name}")

        return await specialist.generate_response(user_input, tool_context, rag_context)


class MockPhi3Specialist:
    """Mock Phi-3 specialist for testing (replace with actual fine-tuned models)."""

    def __init__(self, domain: str, description: str):
        self.domain = domain
        self.description = description

    async def generate_response(
        self,
        user_input: str,
        tool_context: ToolClassification,
        rag_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate specialist response with tool calls."""

        # Mock response based on domain
        if self.domain == "mathematics":
            response_text = f"Let me help you with that math problem. {user_input}"
            tool_calls = [
                {"tool": tool, "parameters": tool_context.parameters}
                for tool in tool_context.tools_needed
            ]

        elif self.domain == "conversation":
            if "pause" in tool_context.parameters.get("action_type", ""):
                response_text = "I'll pause here for you."
            else:
                response_text = "How can I help you with your question?"
            tool_calls = [
                {"tool": tool, "parameters": {}} for tool in tool_context.tools_needed
            ]

        else:
            response_text = (
                f"As your {self.domain} specialist, I'll help with: {user_input}"
            )
            tool_calls = [
                {"tool": tool, "parameters": {}} for tool in tool_context.tools_needed
            ]

        return {
            "text": response_text,
            "tool_calls": tool_calls,
            "specialist": self.domain,
            "confidence": tool_context.confidence,
        }


class PiperTTSEngine:
    """Integration with existing Piper TTS setup."""

    def __init__(self):
        self.piper_bin = os.getenv("PIPER_BIN", "vendor/piper/piper")
        self.voice_models = {
            "amy": os.getenv("PIPER_MODEL", "models/piper/en_US-amy-low.onnx"),
            "jarvis": os.getenv(
                "PIPER_JARVIS_MODEL", "models/piper/en_GB-alan-low.onnx"
            ),
            "alan": os.getenv("PIPER_ALAN_MODEL", "models/piper/en_GB-alan-low.onnx"),
            "southern_male": os.getenv(
                "PIPER_SOUTHERN_MALE_MODEL",
                "models/piper/en_GB-southern_english_male-low.onnx",
            ),
        }

    async def synthesize(self, text: str, voice: str = "amy") -> bytes:
        """Synthesize speech using Piper TTS."""
        model_path = self.voice_models.get(voice, self.voice_models["amy"])

        # Create temp file for output
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = tmp.name

        try:
            # Run Piper TTS
            cmd = [self.piper_bin, "-m", model_path, "-f", output_path]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=text.encode())

            if proc.returncode != 0:
                raise RuntimeError(f"Piper TTS failed: {stderr.decode()}")

            # Read generated audio
            with open(output_path, "rb") as f:
                audio_data = f.read()

            return audio_data

        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)


class ToolExecutor:
    """Execute tools identified by the tiny controller."""

    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the specified tools."""
        results = {}

        for tool_call in tool_calls:
            tool_name = tool_call["tool"]
            parameters = tool_call.get("parameters", {})

            # Mock tool execution (replace with actual tool implementations)
            if tool_name == "calculator":
                results[tool_name] = f"Calculation result: {parameters}"
            elif tool_name == "latex_renderer":
                results[tool_name] = f"LaTeX rendered: {parameters}"
            elif tool_name == "graphing":
                results[tool_name] = f"Graph generated: {parameters}"
            elif tool_name == "audio_pause":
                results[tool_name] = "Audio paused"
            else:
                results[tool_name] = f"Tool {tool_name} executed with {parameters}"

        return results


class IntegratedAudioPipeline:
    """Complete integrated pipeline: Audio → Tools → Response → Audio."""

    def __init__(self):
        self.whisper = WhisperCPPTranscriber()
        self.tiny_controller = TinyToolController()
        self.phi3_orchestrator = Phi3SpecialistOrchestrator()
        self.piper = PiperTTSEngine()
        self.tool_executor = ToolExecutor()

    async def process_audio(self, audio_data: bytes) -> AudioProcessingResult:
        """Complete audio processing pipeline."""
        import time

        start_time = time.time()

        # 1. Speech to Text (WhisperCPP)
        transcription = await self.whisper.transcribe(audio_data)
        logger.info(f"Transcription: {transcription}")

        # 2. Tool Classification (Tiny Model - Ultra Fast)
        tool_classification = await self.tiny_controller.classify_tools(transcription)
        logger.info(
            f"Tool classification: {tool_classification.primary_category}, confidence: {tool_classification.confidence}"
        )

        # 3. Specialist Response (Phi-3)
        specialist_response = await self.phi3_orchestrator.get_response(
            tool_classification.specialist_required, transcription, tool_classification
        )
        logger.info(f"Specialist: {specialist_response['specialist']}")

        # 4. Tool Execution
        tool_outputs = await self.tool_executor.execute_tools(
            specialist_response["tool_calls"]
        )
        logger.info(f"Tools executed: {list(tool_outputs.keys())}")

        # 5. Text to Speech (Piper)
        audio_output = await self.piper.synthesize(
            specialist_response["text"], voice=tool_classification.voice_preference
        )

        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Total processing time: {processing_time}ms")

        return AudioProcessingResult(
            transcription=transcription,
            tool_classification=tool_classification,
            specialist_response=specialist_response["text"],
            tool_outputs=tool_outputs,
            audio_output=audio_output,
            processing_time_ms=processing_time,
        )


async def demo_integration():
    """Demo the complete integration."""
    print("🎤 Integrated Audio Pipeline Demo")
    print("=" * 50)

    pipeline = IntegratedAudioPipeline()

    # Mock audio data (in real use, this comes from microphone)
    demo_texts = [
        "Solve the equation x squared plus 5x minus 6 equals 0",
        "Wait, let me think about this",
        "Can you show me a graph of y equals x squared?",
        "What is the quadratic formula?",
    ]

    for i, text in enumerate(demo_texts, 1):
        print(f"\n--- Demo {i}: '{text}' ---")

        # Mock audio data (normally from WhisperCPP)
        mock_audio = text.encode()  # In real use, this would be actual audio bytes

        # Simulate just the text processing part for demo
        tool_classification = await pipeline.tiny_controller.classify_tools(text)

        print(f"📂 Category: {tool_classification.primary_category}")
        print(f"🛠️  Tools: {tool_classification.tools_needed}")
        print(f"🧠 Specialist: {tool_classification.specialist_required}")
        print(f"🎯 Confidence: {tool_classification.confidence}")
        print(f"🔊 Voice: {tool_classification.voice_preference}")

        # Get specialist response
        specialist_response = await pipeline.phi3_orchestrator.get_response(
            tool_classification.specialist_required, text, tool_classification
        )

        print(f"💬 Response: {specialist_response['text']}")
        print(f"⚡ Tool calls: {len(specialist_response['tool_calls'])}")


if __name__ == "__main__":
    asyncio.run(demo_integration())
