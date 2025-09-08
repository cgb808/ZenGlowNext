"""Embedding service endpoint.
Provides /model/embed accepting {"texts": [..]} and returning {"embeddings": [...]}
Uses a local sentence-transformers model (configurable via EMBED_MODEL). Falls back to
simple hash-based embedding if transformers not available (never in production ideally).
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_embed_model = None
_model_name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


class EmbedPayload(BaseModel):
    texts: List[str]


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str


def _lazy_load():  # pragma: no cover - heavy path
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _embed_model = SentenceTransformer(_model_name)
    except Exception as e:  # fallback lightweight deterministic embedding
        logging.getLogger(__name__).warning(
            "embedding_model_load_failed_fallback", extra={"load_error": str(e)}
        )
        _embed_model = None
    return _embed_model


def _cheap_embed(text: str, dim: int = 384) -> List[float]:
    # Deterministic hash -> pseudo vector
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # repeat hash bytes to fill dim
    raw = (h * ((dim // len(h)) + 1))[:dim]
    # map bytes to [-1,1]
    vec = [((b / 255.0) * 2.0 - 1.0) for b in raw]
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@router.post("/model/embed", response_model=EmbedResponse)
async def embed_texts(payload: EmbedPayload):
    if not payload.texts:
        raise HTTPException(400, "texts empty")
    model = _lazy_load()
    if model is None:
        # fallback path
        embeds = [_cheap_embed(t) for t in payload.texts]
        return {"embeddings": embeds, "model": "cheap-hash-fallback"}
    try:
        embeds = model.encode(payload.texts, normalize_embeddings=True).tolist()
    except Exception as e:
        raise HTTPException(500, f"embedding_failed: {e}")
    return {"embeddings": embeds, "model": _model_name}
