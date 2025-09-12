"""
Health check endpoints for ZenGlow Indexer API.

Refactored to support asynchronous, non-blocking checks and multi-DB health via
DBManager when available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import APIRouter, Response, Depends, Request
import json
import asyncio
import os
import httpx

from .system_metrics import get_system_metrics
from app.core.deps import get_db_manager
try:
    from app.rag.db_manager import DBManager  # type: ignore
except Exception:
    DBManager = None  # type: ignore


class ModelRecord(TypedDict, total=False):
    name: str
    family: str
    quant: Optional[str]
    context_len: Optional[int]
    role: Optional[str]
    loaded: bool
    throughput_tps: Optional[float]


@dataclass
class QueryStats:
    total: int = 0
    cache_hits: Dict[str, int] = field(
        default_factory=lambda: {"full": 0, "feature": 0, "none": 0}
    )
    latencies_ms: List[float] = field(default_factory=list)
    last_latency_ms: Optional[float] = None


model_registry: List[ModelRecord] = []
query_stats = QueryStats()
MAX_LAT_SAMPLES = 200


def register_model(
    name: str,
    family: str,
    quant: Optional[str] = None,
    context_len: Optional[int] = None,
    role: Optional[str] = None,
    loaded: bool = False,
    throughput_tps: Optional[float] = None,
) -> None:
    existing = next((m for m in model_registry if m.get("name") == name), None)
    record: ModelRecord = ModelRecord(
        name=name,
        family=family,
        quant=quant,
        context_len=context_len,
        role=role,
        loaded=loaded,
        throughput_tps=throughput_tps,
    )
    if existing:
        existing.update(record)  # type: ignore[arg-type]
    else:
        model_registry.append(record)


# Seed (can be updated at startup elsewhere)
register_model(
    "gemma:2b",
    family="gemma",
    quant="q4_0",
    context_len=8192,
    role="generation",
    loaded=True,
    throughput_tps=35.0,
)
register_model(
    "bge-small",
    family="bge",
    quant="fp16",
    context_len=1024,
    role="embedding",
    loaded=False,
    throughput_tps=120.0,
)


def get_model_registry() -> List[ModelRecord]:
    return list(model_registry)


def record_query_stats(
    latency_sec: float, cache_hit: str
) -> None:  # called from ranking_router
    ms = latency_sec * 1000.0
    query_stats.total += 1
    if cache_hit not in query_stats.cache_hits:
        query_stats.cache_hits[cache_hit] = 0
    query_stats.cache_hits[cache_hit] += 1
    query_stats.last_latency_ms = ms
    query_stats.latencies_ms.append(ms)
    if len(query_stats.latencies_ms) > MAX_LAT_SAMPLES:
        query_stats.latencies_ms = query_stats.latencies_ms[-MAX_LAT_SAMPLES:]


def get_query_stats_snapshot() -> Dict[str, Any]:
    lat: List[float] = query_stats.latencies_ms
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    if lat:
        ordered: List[float] = sorted(lat)
        n = len(ordered) - 1
        p50 = ordered[int(0.5 * n)]
        p95 = ordered[int(0.95 * n)]
        p99 = ordered[int(0.99 * n)]
    snapshot: Dict[str, Any] = {
        "total": query_stats.total,
        "cache_hits": dict(query_stats.cache_hits),
        "latencies_ms": list(lat),
        "last_latency_ms": query_stats.last_latency_ms,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
    }
    return snapshot


health_router = APIRouter()


@health_router.get("/health")
async def health_root() -> Dict[str, Any]:
    """Root health check."""
    return {"status": "ok"}


@health_router.get("/health/ollama")
async def health_ollama() -> Dict[str, Any]:
    """Check Ollama service health by querying its /api/tags endpoint.
    Returns status and (truncated) model tags if available.
    """
    base = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
    url = f"{base}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return {"ollama": "fail", "status_code": r.status_code}
        data = r.json()
        models = [m.get("name") for m in data.get("models", [])][:10]
        return {"ollama": "ok", "models": models, "count": len(models)}
    except Exception as e:  # pragma: no cover - network/env dependent
        return {"ollama": "fail", "error": str(e)}


@health_router.get("/health/db")
async def health_db(db_manager: Optional["DBManager"] = Depends(get_db_manager)) -> Dict[str, Any]:
    """Check health of all configured DB pools via DBManager; fallback to disabled."""
    if not db_manager or not getattr(db_manager, "pools", None):
        last_err = os.getenv("DB_CLIENT_LAST_ERROR")
        return {"overall_status": "degraded", "reason": "no database pools configured", "last_error": last_err, "databases": {}}

    async def ping_db(name: str) -> Dict[str, Any]:
        client = db_manager.get_client(name)
        if not client:
            return {name: {"status": "misconfigured"}}
        try:
            row = await client.execute_query("SELECT 1;", fetch="one")
            if row and (row[0] == 1 or row.get("?column?", 0) == 1 if isinstance(row, dict) else False):
                return {name: {"status": "ok"}}
            return {name: {"status": "unhealthy", "error": "no result"}}
        except Exception as e:
            return {name: {"status": "unhealthy", "error": str(e)}}

    tasks = [ping_db(n) for n in db_manager.pools.keys()]
    results = await asyncio.gather(*tasks)
    db_status: Dict[str, Any] = {}
    for r in results:
        db_status.update(r)
    overall_ok = all(v.get("status") == "ok" for v in db_status.values())
    return {"overall_status": "ok" if overall_ok else "degraded", "databases": db_status}


@health_router.get("/health/models")
async def health_models() -> Dict[str, Any]:
    """Return model registry metadata."""
    return {"models": get_model_registry()}


@health_router.get("/metrics/json")
async def json_metrics() -> Dict[str, Any]:
    """JSON subset of key RAG metrics (complements Prometheus)."""
    return {
        "query_stats": get_query_stats_snapshot(),
        "models": get_model_registry(),
        "system": get_system_metrics(),
    }


@health_router.get("/health/aggregated")
async def health_aggregated(request: Request) -> Dict[str, Any]:
    """Aggregated health status for all services for dashboard display."""
    try:
        # Check database (explicitly fetch manager via request)
        db_result = await health_db(db_manager=get_db_manager(request))  # type: ignore[arg-type]
        db_status = "healthy" if db_result.get("overall_status") == "ok" else "degraded"

        # Check Ollama
        ollama_result = await health_ollama()
        ollama_status = (
            "healthy" if ollama_result.get("ollama") == "ok" else "unhealthy"
        )

        # Check models
        models = get_model_registry()
        loaded_models = [m for m in models if m.get("loaded", False)]
        models_status = "healthy" if len(loaded_models) > 0 else "degraded"

        # System metrics
        system_metrics = get_system_metrics()
        cpu_usage = system_metrics.get("cpu_percent", 0)
        memory_usage = system_metrics.get("memory_percent", 0)
        system_status = "healthy"
        if cpu_usage > 80 or memory_usage > 85:
            system_status = "degraded"
        elif cpu_usage > 95 or memory_usage > 95:
            system_status = "unhealthy"

        # Overall status
        statuses = [db_status, ollama_status, models_status, system_status]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "services": {
                "database": {"status": db_status, "details": db_result},
                "ollama": {"status": ollama_status, "details": ollama_result},
                "models": {
                    "status": models_status,
                    "loaded_count": len(loaded_models),
                    "total_count": len(models),
                },
                "system": {
                    "status": system_status,
                    "cpu_percent": cpu_usage,
                    "memory_percent": memory_usage,
                },
            },
            "timestamp": system_metrics.get("timestamp"),
            "uptime_seconds": system_metrics.get("uptime_seconds"),
        }
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": get_system_metrics().get("timestamp"),
        }


# ---------------- Prometheus Metrics -----------------
try:
    from prometheus_client import CONTENT_TYPE_LATEST  # type: ignore
    from prometheus_client import Counter, Histogram, generate_latest

    RAG_QUERY_COUNT = Counter("rag_query_total", "Total RAG queries processed", ["endpoint", "cache_hit"])  # type: ignore[var-annotated]
    RAG_QUERY_LATENCY = Histogram(  # type: ignore[var-annotated]
        "rag_query_latency_seconds",
        "Latency for RAG query processing (fusion end-to-end)",
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
    )

    @health_router.get("/metrics")
    def metrics_endpoint() -> Response:  # pragma: no cover (exposed for Prometheus)
        # Base exposition
        base = generate_latest().decode()
        # Augment with lightweight system metrics (GPU + docker) without allocating a new registry
        from .system_metrics import get_system_metrics
        lines = [base.rstrip()]  # preserve trailing newline handling
        try:
            sysm = get_system_metrics()
            for gpu in sysm.get("gpu", []):
                idx = gpu.get("index")
                for field in (
                    "memory_used_mb",
                    "memory_total_mb",
                    "memory_percent",
                    "utilization_percent",
                    "temperature_c",
                ):
                    val = gpu.get(field)
                    if isinstance(val, (int, float)):
                        lines.append(f"app_gpu_{field}{{index=\"{idx}\"}} {val}")
            for proc in sysm.get("gpu_processes", []):
                pid = proc.get("pid")
                name = proc.get("process")
                mem = proc.get("memory_used_mb")
                if isinstance(mem, (int, float)):
                    lines.append(f"app_gpu_process_memory_used_mb{{pid=\"{pid}\",process=\"{name}\"}} {mem}")
            for c in sysm.get("containers", []):
                cname = c.get("name") or c.get("id")
                for field in ("cpu_percent", "memory_used_bytes", "memory_percent"):
                    val = c.get(field)
                    if isinstance(val, (int, float)):
                        lines.append(f"app_container_{field}{{name=\"{cname}\"}} {val}")
        except Exception:
            pass
        payload = "\n".join(lines) + "\n"
        return Response(payload, media_type=CONTENT_TYPE_LATEST)

except Exception:  # pragma: no cover - metrics optional if dependency missing

    @health_router.get("/metrics")
    def metrics_endpoint() -> Response:  # type: ignore[unused-ignore]
        return Response("", media_type="text/plain")
