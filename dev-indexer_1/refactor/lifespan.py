"""Application lifespan manager

Combines optional single async DB pool (DB_ASYNC_POOL=1) and multi-DB DBManager
(DB_MULTI_ENABLED=1) into a single FastAPI lifespan generator.

Precedence: when DB_MULTI_ENABLED=1, we initialize DBManager only (each DB gets
its own pool). The single-pool path is used only for backward compatibility when
multi-DB is disabled. Defaults remain safe: if flags are off or optional deps are
missing, it no-ops.
"""
from __future__ import annotations

import os
from typing import AsyncIterator, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI

try:  # optional dependency
    from psycopg_pool import AsyncConnectionPool
except Exception:  # pragma: no cover - optional
    AsyncConnectionPool = None  # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    single_pool: Optional[AsyncConnectionPool] = None  # type: ignore[name-defined]
    db_manager: Optional[DBManager] = None

    # Short-circuit for tests wanting to skip DB init entirely
    if os.getenv("APP_TEST_MODE") == "1" and os.getenv("SKIP_DB", "1") == "1":
        yield
        return

    try:
        # Multi-DB manager (preferred): each logical DB gets its own pool.
        if os.getenv("DB_MULTI_ENABLED", "0") == "1":
            try:
                from app.rag.db_manager import DBManager  # local import
                db_manager = DBManager()
                if db_manager.startup():
                    setattr(app.state, "db_manager", db_manager)
                    # Back-compat alias: expose general pool as db_pool if present
                    if getattr(db_manager, "pools", None) and "general" in db_manager.pools:
                        setattr(app.state, "db_pool", db_manager.pools["general"])  # type: ignore[index]
            except Exception:  # pragma: no cover - defensive in environments without optional deps
                db_manager = None
        # Single async pool (legacy/compat) only if multi-DB not enabled
        elif os.getenv("DB_ASYNC_POOL", "0") == "1" and AsyncConnectionPool is not None:
            single_pool = AsyncConnectionPool(
                conninfo=os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:password@localhost:5432/rag_db",
                ),
                min_size=int(os.getenv("DB_POOL_MIN", 2)),
                max_size=int(os.getenv("DB_POOL_MAX", 10)),
                timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
            )
            setattr(app.state, "db_pool", single_pool)

        yield
    finally:
        # Shutdown in reverse order
        if db_manager is not None:
            try:
                await db_manager.shutdown()
            except Exception:  # pragma: no cover - defensive
                pass
        if single_pool is not None:
            try:
                await single_pool.close()
            except Exception:  # pragma: no cover - defensive
                pass


__all__ = ["lifespan"]
