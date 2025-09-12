"""
Operational diagnostics endpoints - Refactored for Asynchronous Operations

This router has been updated to be fully non-blocking. It leverages asyncio
for network operations, preventing the diagnostics checks from interfering with
the main application's performance. It is also aware of the new multi-DB strategy.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/env")
def env_snapshot() -> Dict[str, Any]:
    """Provides a snapshot of relevant environment variables."""
    wanted = [
        "DATABASE_URL",
        "PII_DATABASE_URL",
        "SPECIALIST_DATABASE_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "SUPABASE_URL",
        "OLLAMA_URL",
    ]
    snap = {k: os.getenv(k) for k in wanted if os.getenv(k) is not None}
    return {"env": snap}


@router.get("/imports")
def import_status() -> Dict[str, Any]:
    """Checks for the presence of key libraries."""
    # Updated to check for the correct async-compatible libraries
    modules = ["psycopg", "psycopg_pool", "redis", "httpx", "numpy", "sentence_transformers"]
    status = {}
    for m in modules:
        try:
            importlib.import_module(m)
            status[m] = "ok"
        except ImportError:
            status[m] = "missing"
    return {"imports": status}


async def _tcp_probe_async(host: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
    """Asynchronously probes a single TCP host and port."""
    try:
        # asyncio.open_connection is the non-blocking equivalent of socket.create_connection
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return {"ok": True, "host": host, "port": port}
    except Exception as e:
        return {"ok": False, "host": host, "port": port, "error": f"{type(e).__name__}"}


@router.get("/summary")
async def quick_summary() -> Dict[str, Any]:
    """Asynchronously generates a quick summary of system connectivity."""
    env = env_snapshot()["env"]
    imports = import_status()["imports"]
    
    check_tasks = []

    # Helper to parse DSNs like 'postgresql://user:pass@host:port/db'
    def parse_dsn(dsn_string: str) -> tuple[str, int] | None:
        try:
            after_at = dsn_string.split("@", 1)[1]
            host_port = after_at.split("/", 1)[0]
            host = host_port.split(":")[0]
            port = int(host_port.split(":")[1]) if ":" in host_port else 5432
            return host, port
        except (IndexError, ValueError):
            return None

    # Create a probe task for each defined database URL
    db_urls = {
        "db_general_tcp": env.get("DATABASE_URL"),
        "db_pii_tcp": env.get("PII_DATABASE_URL"),
        "db_specialist_tcp": env.get("SPECIALIST_DATABASE_URL"),
    }
    for key, url in db_urls.items():
        if url and (parsed := parse_dsn(url)):
            host, port = parsed
            check_tasks.append(_tcp_probe_async(host, port))

    # Create a probe task for Redis
    redis_host = env.get("REDIS_HOST")
    redis_port = env.get("REDIS_PORT")
    if redis_host and redis_port:
        check_tasks.append(_tcp_probe_async(redis_host, int(redis_port)))

    # Run all network probes concurrently
    results = await asyncio.gather(*check_tasks)
    
    # Format the results into a dictionary
    checks = {}
    for res in results:
        # Determine the key for the checks dictionary
        key = "redis_tcp" if res.get("host") == redis_host else next(
            (k for k, v in db_urls.items() if v and res.get("host") in v), "unknown_tcp"
        )
        checks[key] = res

    return {"env": env, "imports": imports, "checks": checks}

__all__ = ["router"]
