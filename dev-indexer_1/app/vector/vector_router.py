"""Vector router (minimal, in-memory stub).

Exposes simple status/version endpoints so the app can boot without the
full vector stack. Safe to replace with a real implementation later.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter


router = APIRouter(prefix="/vector", tags=["vector"])

_vector_count = 0  # simplistic placeholder; increment via add endpoint later


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
