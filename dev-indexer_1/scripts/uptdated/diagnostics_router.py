"""Operational diagnostics endpoints.

Endpoints provide quick visibility when "nothing works" without needing
external shell access. They intentionally avoid heavy dependencies.
"""

from __future__ import annotations

import importlib
import os
import socket
import time
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/env")
def env_snapshot() -> Dict[str, Any]:  # pragma: no cover - simple accessor
    wanted = [
        "DATABASE_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "OLLAMA_URL",
        "OLLAMA_MODEL",
        "LLAMA_CPP_SERVER_URL",
        "EMBED_ENDPOINT",
    ]
    snap = {k: os.getenv(k) for k in wanted if os.getenv(k) is not None}
    return {"env": snap}


@router.get("/imports")
def import_status() -> Dict[str, Any]:
    modules = ["psycopg2", "redis", "requests", "numpy"]
    status = {}
    for m in modules:
        try:
            importlib.import_module(m)
            status[m] = True
        except Exception as e:  # pragma: no cover - defensive
            status[m] = f"missing: {e.__class__.__name__}: {e}"  # noqa: PERF401
    return {"imports": status}


@router.get("/tcp")
def tcp_probe(host: str, port: int, timeout: float = 1.0):
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.time() - start) * 1000.0
            return {"ok": True, "latency_ms": elapsed}
    except Exception as e:  # pragma: no cover - network variability
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


@router.get("/summary")
def quick_summary():
    # Light composite view useful for initial triage
    env = env_snapshot()["env"]
    imports = import_status()["imports"]
    checks = {}
    # Heuristic connectivity checks (only if env present)
    if env.get("REDIS_HOST") and env.get("REDIS_PORT"):
        try:
            pr = tcp_probe(env["REDIS_HOST"], int(env["REDIS_PORT"]))
        except Exception as e:  # noqa: BLE001
            pr = {"ok": False, "error": str(e)}
        checks["redis"] = pr
    if env.get("DATABASE_URL"):
        # parse host: assume pattern driver://user:pass@host:port/db
        dsn = env["DATABASE_URL"]
        host_port = None
        try:
            after_at = dsn.split("@", 1)[1]
            host_port = after_at.split("/", 1)[0]
            host = host_port.split(":")[0]
            port = int(host_port.split(":")[1]) if ":" in host_port else 5432
            checks["db_tcp"] = tcp_probe(host, port)
        except Exception:
            checks["db_tcp"] = {"ok": False, "error": "parse_failed"}
    return {"env": env, "imports": imports, "checks": checks}


__all__ = ["router"]
