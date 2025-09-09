from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore


router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/ping")
async def ping() -> dict[str, Any]:
    return {"ok": True}


@router.get("/redis")
async def diag_redis() -> dict[str, Any]:
    if redis is None:
        return {"ok": False, "error": "redis-py not installed"}
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        r = redis.StrictRedis(host=host, port=port, socket_connect_timeout=1.5)
        pong = r.ping()
        return {"ok": bool(pong), "host": host, "port": port}
    except Exception as e:  # pragma: no cover
        return {"ok": False, "host": host, "port": port, "error": str(e)}


@router.get("/db")
async def diag_db() -> dict[str, Any]:
    if psycopg2 is None:
        return {"ok": False, "error": "psycopg2 not installed"}
    dsn = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/rag_db",
    )
    try:
        with psycopg2.connect(dsn, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT now()")
                now_row = cur.fetchone()
        now_val = str(now_row[0]) if (now_row and len(now_row) > 0) else None
        return {"ok": True, "now": now_val}
    except Exception as e:  # pragma: no cover
        return {"ok": False, "dsn": dsn, "error": str(e)}
