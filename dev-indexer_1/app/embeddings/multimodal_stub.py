"""
Multimodal Embeddings Stub

Placeholder interfaces for image/audio embeddings (e.g., CLIP, speech encoders).
Wire real models when ready; keep CCE interface stable.
"""
from __future__ import annotations
from typing import Iterable, List, Optional, Any


def embed_image(pixels: Any, *, model: str = "clip-vit-b32") -> List[float]:
    # TODO: integrate OpenCLIP or equivalent
    return []


def embed_audio(waveform: Any, *, model: str = "speech-small") -> List[float]:
    # TODO: integrate a speech embedding model
    return []


def fuse_embeddings(parts: Iterable[List[float]], weights: Optional[Iterable[float]] = None) -> List[float]:
    # TODO: implement real fusion; currently returns first available
    for vec in parts:
        if vec:
            return vec
    return []
