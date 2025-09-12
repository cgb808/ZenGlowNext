"""Vector router (minimal, in-memory stub).

Exposes simple status/version endpoints so the app can boot without the
full vector stack. Safe to replace with a real implementation later.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from app.db.async_db import get_async_db_client as _get_async_db_client  # type: ignore[attr-defined]
from app.rag.embedder import Embedder  # type: ignore[attr-defined]


router = APIRouter(prefix="/vector", tags=["vector"])

_vector_count = 0  # simplistic placeholder; increment via add endpoint later
_embedder = Embedder()


@router.get("/status")
async def vector_status() -> Dict[str, Any]:  # pragma: no cover - trivial
    return {"ok": True, "component": "vector", "mode": "stub"}


@router.get("/version")
async def vector_version() -> Dict[str, int]:  # pragma: no cover - trivial
    return {"version": 1}


@router.get("/ping")
async def vector_ping() -> dict[str, Any]:  # pragma: no cover - trivial
    return {"ok": True, "count": _vector_count}


@router.get("/index")
async def vector_index_status() -> dict[str, Any]:  # pragma: no cover - trivial
    return {"count": _vector_count, "backend": "stub"}


@router.get("/search_async")
async def vector_search_async(q: str = Query(..., min_length=1), top_k: int = 5, db=Depends(_get_async_db_client)):
    if not db:
        return {"results": [], "enabled": False}
    vec = _embedder.embed_batch([q])[0]
    rows = await db.vector_search(vec, top_k=top_k)
    return {"results": rows, "enabled": True}


@router.get("/search_hybrid")
async def vector_search_hybrid(
    q: str = Query(..., min_length=1),
    top_k: int = 10,
    user_id: str | None = None,
    db=Depends(_get_async_db_client),
):
    if not db:
        return {"results": [], "enabled": False}
    vec = _embedder.embed_batch([q])[0]
    filters = {"user_id": user_id} if user_id else None
    fused = await db.hybrid_search(q, vec, top_k=top_k, filters=filters)
    return {"results": fused, "enabled": True, "hybrid": True}
