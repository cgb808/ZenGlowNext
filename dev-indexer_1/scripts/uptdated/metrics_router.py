"""Metrics endpoints (dashboard + basic snapshot).

Cherry-picked and adapted from Supabase Edge function versions in
`dashboard_handoff` folder so the dashboard can query the FastAPI app
directly when running locally (no edge functions required).

Endpoints:
  GET /metrics/basic    -> lightweight in-process counters/latencies
  GET /metrics/dashboard -> dashboard JSON shape (queue, embeddings, runtime, ingest)

Auth:
  If METRICS_API_KEY env var is set, requests must provide header
  `X-Zendexer-Key: <value>` (case insensitive) else 401.

Graceful Degradation:
  If optional tables (queue, runtime_metrics, ingest log) are missing the
  endpoint will omit those sections instead of failing entirely.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import psycopg  # psycopg3 driver
from psycopg import sql
from fastapi import APIRouter, HTTPException, Request

from app.core import metrics as inproc_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

WINDOWS: List[tuple[str, int]] = [  # (label, seconds)
    ("5m", 5 * 60),
    ("1h", 60 * 60),
]

QUEUE_TABLE = os.getenv("QUEUE_TABLE", "code_chunk_ingest_queue")
INGEST_LOG_TABLE = os.getenv("INGEST_LOG_TABLE", "code_chunk_ingest_log")
RUNTIME_METRICS_TABLE = os.getenv("RUNTIME_METRICS_TABLE", "runtime_metrics")


def _require_key(req: Request) -> None:
    expected = os.getenv("METRICS_API_KEY") or os.getenv("ZENDEXER_INGEST_KEY")
    if not expected:
        return  # no auth enforced
    provided = (
        req.headers.get("X-Zendexer-Key")
        or req.headers.get("x-zendexer-key")
        or req.headers.get("X-ZENDEXER-KEY")
    )
    if provided != expected:
        raise HTTPException(401, "unauthorized")


def _pg_conn():
    """Obtain a psycopg3 connection.

    psycopg3 accepts the same DSN string we used for psycopg2. Autocommit
    semantics: in this module we rely only on simple SELECT statements so
    implicit transaction handling is fine. Using context manager to ensure
    closure. Caller uses `with _pg_conn() as conn`.
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(500, "DATABASE_URL not set")
    return psycopg.connect(dsn)


@router.get("/basic")
def basic_metrics() -> Dict[str, Any]:
    """Return in-process metrics snapshot (no DB usage)."""
    snap = inproc_metrics.snapshot()
    snap["ts"] = datetime.utcnow().isoformat()
    return snap


@router.get("/dashboard")
def dashboard_metrics(request: Request) -> Dict[str, Any]:  # noqa: D401
    _require_key(request)
    out: Dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(),
        "windows": [w for w, _ in WINDOWS],
    }

    # Queue stats ---------------------------------------------------------
    try:
        with _pg_conn() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT status, COUNT(id) FROM {} GROUP BY status").format(
                    sql.Identifier(QUEUE_TABLE)
                )
            )
            rows = cur.fetchall()
            out["queue"] = [
                {"status": r[0], "count": int(r[1])} for r in rows if r and len(r) >= 2
            ]
            # oldest pending age
            cur.execute(
                sql.SQL(
                    "SELECT created_at FROM {} WHERE status='pending' ORDER BY created_at ASC LIMIT 1"
                ).format(sql.Identifier(QUEUE_TABLE))
            )
            row = cur.fetchone()
            if row and row[0]:
                try:
                    created_ts = row[0]
                    if isinstance(created_ts, str):  # fallback parse
                        created_dt = datetime.fromisoformat(
                            created_ts.replace("Z", "+00:00")
                        )
                    else:
                        created_dt = created_ts
                    age_s = int(
                        (datetime.now(timezone.utc) - created_dt).total_seconds()
                    )
                    out["queue_oldest_pending_age_s"] = age_s
                except Exception:
                    pass
    except Exception:
        # queue table may not exist
        pass

    # Doc embeddings count -----------------------------------------------
    try:
        with _pg_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(id) FROM doc_embeddings")
            c = cur.fetchone()
            out["doc_embeddings"] = [
                {"count": int(c[0]) if c and c[0] is not None else 0}
            ]
    except Exception:
        pass

    # Runtime metrics aggregation ----------------------------------------
    runtime_stats: Dict[str, List[Dict[str, Any]]] = {}
    try:
        with _pg_conn() as conn, conn.cursor() as cur:
            for label, seconds in WINDOWS:
                since = datetime.utcnow() - timedelta(seconds=seconds)
                try:
                    cur.execute(
                        sql.SQL(
                            "SELECT metric, value FROM {} WHERE collected_at >= %s"
                        ).format(sql.Identifier(RUNTIME_METRICS_TABLE)),
                        (since,),
                    )
                except Exception:
                    continue
                rows = cur.fetchall() or []
                values: Dict[str, List[float]] = {}
                for metric, value in rows:
                    if isinstance(value, (int, float)):
                        values.setdefault(metric, []).append(float(value))
                stats_list: List[Dict[str, Any]] = []
                for metric, arr in values.items():
                    arr.sort()
                    n = len(arr)
                    if n == 0:
                        continue

                    def pct(p: float) -> float:
                        idx = min(n - 1, int(p * (n - 1)))
                        return arr[idx]

                    stats_list.append(
                        {
                            "metric": metric,
                            "window": label,
                            "count": n,
                            "avg": sum(arr) / n,
                            "p50": pct(0.5),
                            "p95": pct(0.95),
                        }
                    )
                runtime_stats[label] = stats_list
    except Exception:
        pass
    if runtime_stats:
        out["runtime_stats"] = runtime_stats

    # Ingest log counts ---------------------------------------------------
    ingest_log: Dict[str, List[Dict[str, Any]]] = {}
    try:
        with _pg_conn() as conn, conn.cursor() as cur:
            for label, seconds in WINDOWS:
                since = datetime.utcnow() - timedelta(seconds=seconds)
                try:
                    cur.execute(
                        sql.SQL(
                            "SELECT status, COUNT(id) FROM {} WHERE created_at >= %s GROUP BY status"
                        ).format(sql.Identifier(INGEST_LOG_TABLE)),
                        (since,),
                    )
                except Exception:
                    continue
                rows = cur.fetchall() or []
                ingest_log[label] = [
                    {"status": r[0], "count": int(r[1])}
                    for r in rows
                    if r and len(r) >= 2
                ]
    except Exception:
        pass
    if ingest_log:
        out["ingest_log"] = ingest_log

    return out
