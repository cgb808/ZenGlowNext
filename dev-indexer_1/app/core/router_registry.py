"""Lightweight router registry utilities.

Currently focused on audio routers to reduce repetitive try/except import
blocks in `main.py`. The intent is to expand this pattern gradually to other
router groups (RAG, system, experimental) without a sweeping refactor.

Design:
  - RouterSpec captures the minimal data needed to attempt an import.
  - Two loader modes supported:
        * module: import module object (expected to expose `.router` attr)
        * direct: import symbol that is already an APIRouter instance
  - Failures are swallowed; caller receives (name -> object | None) mapping.

This keeps startup resilient when optional heavy dependencies are absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Dict, List


@dataclass(slots=True)
class RouterSpec:
    name: str                 # key in results dict
    import_path: str          # e.g. "app.audio.devices_router"
    mode: str = "module"      # "module" | "direct"
    attr: str = "router"      # attribute to fetch when mode == direct


def load_router_specs(specs: List[RouterSpec]) -> Dict[str, Any]:  # pragma: no cover - import side-effects
    results: Dict[str, Any] = {}
    for spec in specs:
        try:
            if spec.mode == "module":
                results[spec.name] = import_module(spec.import_path)
            else:  # direct
                module_path, _, symbol = spec.import_path.rpartition(".")
                if not module_path:
                    # Fallback: treat import_path as module and pull attr
                    module = import_module(spec.import_path)
                    results[spec.name] = getattr(module, spec.attr)
                else:
                    module = import_module(module_path)
                    results[spec.name] = getattr(module, symbol)
        except Exception:  # noqa: BLE001 - intentionally soft
            results[spec.name] = None
    return results


# Predefined audio router specs (order not critical, but grouped for readability)
AUDIO_ROUTER_SPECS: List[RouterSpec] = [
    RouterSpec("devices_router", "app.audio.devices_router", mode="module"),
    RouterSpec("transcription_router", "app.audio.transcription_router", mode="module"),
    RouterSpec("tts_router", "app.audio.tts_router", mode="module"),
    RouterSpec("speaker_router", "app.audio.speaker_router.router", mode="direct"),
    RouterSpec("wake_router", "app.audio.wake_router.router", mode="direct"),
    RouterSpec("xtts_router", "app.audio.xtts_router.router", mode="direct"),
    RouterSpec("piper_router", "app.audio.piper_tts_router.router", mode="direct"),
]
