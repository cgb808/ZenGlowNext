from __future__ import annotations
from fastapi import APIRouter
from . import response_cache, cache_metrics

router = APIRouter(prefix="/internal/cache", tags=["cache"])


@router.get("/stats")
def stats():  # pragma: no cover - simple
    base = response_cache.cache_stats()
    # merge all counters
    base.update(cache_metrics.snapshot())
    return base
