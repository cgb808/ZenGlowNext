from __future__ import annotations

import asyncio
import importlib
import os
from typing import Any, Dict

from fastapi import APIRouter

try:  # optional deps
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


@router.get("/env")
def env_snapshot() -> Dict[str, Any]:
    # Minimal filtered snapshot: reuse existing config helper if present
    try:
        from app.core.config import get_sanitized_env_snapshot  # type: ignore

        env = get_sanitized_env_snapshot()
    except Exception:
        # Fallback: include a few safe prefixes
        prefixes = ("PG_", "RAG_", "OLLAMA_", "CORS_", "EMBED_", "ASYN")
        env = {k: v for k, v in os.environ.items() if any(k.startswith(p) for p in prefixes)}
    return {"env": env}


@router.get("/imports")
def import_status() -> Dict[str, Any]:
    modules = ["psycopg", "psycopg2", "redis", "numpy", "sentence_transformers"]
    status: Dict[str, Any] = {}
    for m in modules:
        try:
            importlib.import_module(m)
            status[m] = True
        except Exception as e:  # pragma: no cover - environment dependent
            status[m] = f"missing: {type(e).__name__}"
    # Version hints
    try:
        import psycopg  # type: ignore

        status["psycopg_version"] = getattr(psycopg, "__version__", "unknown")
    except Exception:
        pass
    return {"imports": status}


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


@router.get("/tcp")
async def tcp_probe(host: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return {"ok": True, "host": host, "port": port}
    except Exception as e:
        return {"ok": False, "host": host, "port": port, "error": f"{type(e).__name__}: {e}"}


@router.get("/summary")
async def quick_summary() -> Dict[str, Any]:
    try:
        from app.core.config import get_sanitized_env_snapshot  # type: ignore

        env = get_sanitized_env_snapshot()
    except Exception:
        env = {}
    imports = import_status()["imports"]

    # Concurrent TCP checks
    tasks = []
    redis_host = env.get("REDIS_HOST") or os.getenv("REDIS_HOST")
    redis_port = env.get("REDIS_PORT") or os.getenv("REDIS_PORT")
    if redis_host and redis_port:
        try:
            tasks.append(tcp_probe(str(redis_host), int(redis_port)))
        except Exception:
            pass
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            after_at = db_url.split("@", 1)[1]
            host_port = after_at.split("/", 1)[0]
            host = host_port.split(":")[0]
            port = int(host_port.split(":")[1]) if ":" in host_port else 5432
            tasks.append(tcp_probe(host, port))
        except Exception:
            pass
    results = await asyncio.gather(*tasks, return_exceptions=True)
    checks: Dict[str, Any] = {}
    for res in results:
        if isinstance(res, dict) and "host" in res:
            if redis_host and res.get("host") == redis_host:
                checks["redis_tcp"] = res
            else:
                checks["db_tcp"] = res
    return {"env": env, "imports": imports, "checks": checks}
