"""Swarm Event Logger

Lightweight append-only JSONL logger for swarm route / feedback / optimize events.
Environment Variables:
  SWARM_EVENT_LOG_PATH: If set, JSONL file path used. Defaults to 'data/swarm_events.jsonl'.
  SWARM_EVENT_LOG_DISABLE: If '1', disables logging entirely.

Hashing:
  query_hash = sha256(lower(trim(query_text)))
  path_hash  = sha256(sorted factors + sorted parameter keys) for optimization candidates.

Intentionally minimal; real deployment could push directly into Postgres (swarm_events table)
or a message queue. This local file log seeds future model training & analytics.
"""
from __future__ import annotations
import os, json, hashlib, threading, time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

_lock = threading.Lock()
_db_initialized = False
_db_available = False
_db_conn = None

def _db_enabled() -> bool:
    return os.getenv("SWARM_EVENT_DB") == "1"

def _db_dsn() -> str:
    return os.getenv("SWARM_EVENT_DB_DSN", "")

def _init_db():
    global _db_initialized, _db_available, _db_conn
    if _db_initialized:
        return
    _db_initialized = True
    if not _db_enabled():
        return
    dsn = _db_dsn()
    if not dsn:
        return
    try:
        import psycopg
        _db_conn = psycopg.connect(dsn, autocommit=True)
        _db_available = True
    except Exception:
        _db_available = False

def _insert_db(record: dict):
    global _db_conn
    if not _db_available or _db_conn is None:
        return
    try:
        cur = _db_conn.cursor()  # type: ignore[attr-defined]
        cols = []
        vals = []
        for k, v in record.items():
            # Map json friendly fields only
            if k in {"ts"}: # skip: ts handled by default now()
                continue
            if k in {"event_type","session_id","user_hash","query_text","query_hash","path_hash","partition_id","swarm_type","success","latency_ms","quality_signal"}:
                cols.append(k)
                vals.append(v)
            elif k == "factors" and v is not None:
                cols.append("factors")
                vals.append(json.dumps(v))
            elif k == "parameters" and v is not None:
                cols.append("parameters")
                vals.append(json.dumps(v))
            elif k == "telemetry" and v is not None:
                cols.append("telemetry")
                vals.append(json.dumps(v))
            elif k == "meta" and v is not None:
                cols.append("meta")
                vals.append(json.dumps(v))
            elif k == "event_embedding" and v is not None:
                # Expect list[float]; pass as python array literal if pgvector installed else ignore
                cols.append("event_embedding")
                vals.append(v)
        if not cols:
            return
        placeholders = []
        args = []
        for v in vals:
            if isinstance(v, list):
                placeholders.append("%s")
                args.append(v)
            else:
                placeholders.append("%s")
                args.append(v)
        sql = f"INSERT INTO swarm_events ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
        cur.execute(sql, args)
        cur.close()
    except Exception:
        pass

def _is_disabled() -> bool:
    return os.getenv("SWARM_EVENT_LOG_DISABLE") == "1"

def _log_path() -> str:
    return os.getenv("SWARM_EVENT_LOG_PATH", "data/swarm_events.jsonl")

def _ensure_dir(path: str) -> None:
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)

def stable_sha256(parts: Iterable[str]) -> str:
    h = hashlib.sha256()
    for part in parts:
        if part is None:
            continue
        h.update(part.encode("utf-8"))
        h.update(b"\x1f")  # unit separator
    return h.hexdigest()

def compute_query_hash(query: Optional[str]) -> Optional[str]:
    if not query:
        return None
    norm = query.strip().lower()
    if not norm:
        return None
    return stable_sha256([norm])

def compute_path_hash(factors: Optional[Sequence[str]], parameters: Optional[Mapping[str, object]]) -> Optional[str]:
    if not factors and not parameters:
        return None
    factor_list = sorted(factors) if factors else []
    param_keys = sorted(parameters.keys()) if parameters else []
    return stable_sha256(factor_list + param_keys)

def log_event(**fields) -> None:
    if _is_disabled():
        return
    try:
        _init_db()
        path = _log_path()
        _ensure_dir(path)
        record = {"ts": time.time(), **fields}
        line = json.dumps(record, separators=(",", ":"))
        with _lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        if _db_enabled():
            _insert_db(record)
    except Exception:
        # swallow to avoid impacting request path
        pass

__all__ = [
    "log_event",
    "compute_query_hash",
    "compute_path_hash",
    "stable_sha256",
]
