"""Audio bootstrap utilities.

Extracted from `app.main` as part of decomposition task (phase 2).
Provides a single `load_audio(skip_audio: bool) -> dict[str, Any]` function
returning the same shape previously produced by `_load_audio`.
"""
from __future__ import annotations

from typing import Any


def load_audio(skip_audio: bool) -> dict[str, Any]:  # pragma: no cover - import side effects
    if skip_audio:
        class _StubRouter:
            router = None

        class _StubObj:
            def __getattr__(self, _):  # noqa: D401
                raise RuntimeError("Audio stack disabled (dependencies missing)")

            def register_persona_callback(self, *_, **__):  # no-op
                return None

            def flush_pending(self) -> int:  # no-op
                return 0

        def _noop_session(_s: str) -> None:
            return None

        return {
            "devices_router": _StubRouter(),
            "transcription_router": _StubRouter(),
            "tts_router": _StubRouter(),
            "speaker_router": None,
            "wake_router": None,
            "xtts_router": None,
            "switchr_router": None,
            "transcript_enqueue": _StubObj(),
            "audio_discovery": _StubObj(),
            "activate_tutor_persona": None,
            "get_session_persona": _noop_session,
            "piper_router": None,
        }

    from app.core.router_registry import AUDIO_ROUTER_SPECS, load_router_specs

    loaded = load_router_specs(AUDIO_ROUTER_SPECS)

    class _Null:
        def __getattr__(self, _):  # pragma: no cover - trivial
            return lambda *a, **k: None

    audio: dict[str, Any] = {
        "devices_router": loaded.get("devices_router"),
        "transcription_router": loaded.get("transcription_router"),
        "tts_router": loaded.get("tts_router"),
        "speaker_router": loaded.get("speaker_router"),
        "wake_router": loaded.get("wake_router"),
        "xtts_router": loaded.get("xtts_router"),
        "switchr_router": None,  # decoupled elsewhere
        "transcript_enqueue": _Null(),
        "audio_discovery": _Null(),
        "activate_tutor_persona": None,
        "get_session_persona": lambda _s: None,
        "piper_router": loaded.get("piper_router"),
    }
    return audio
