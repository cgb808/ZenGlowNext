"""FastAPI dependency providers for core services.

Provides centralized Depends helpers for DBManager and async Redis client.
"""
from __future__ import annotations

from typing import Optional, Any
from fastapi import Request

from app.core.redis_async import get_async_redis as _get_async_redis

try:
    # DBManager lives under app.rag
    from app.rag.db_manager import DBManager  # type: ignore
except Exception:  # pragma: no cover - optional in test envs
    DBManager = None  # type: ignore


def get_db_manager(request: Request) -> Optional["DBManager"]:
    """Retrieve the DBManager instance stored on app.state if available."""
    try:
        return getattr(request.app.state, "db_manager", None)
    except Exception:
        return None


def get_async_redis() -> Optional[Any]:
    """Return a cached async Redis client instance, or None if unavailable."""
    return _get_async_redis()


__all__ = ["get_db_manager", "get_async_redis"]
