#!/usr/bin/env python3
"""
Vector Index Tuner for pgvector

Sweep key runtime knobs and report latency/overlap metrics:
- HNSW: hnsw.ef_search
- IVFFlat: ivfflat.probes

It samples existing embeddings from your table as query vectors, runs
ORDER BY embedding <-> $query LIMIT K, and measures average latency.
Optionally computes an approximate "overlap recall" by comparing results
against a high-setting baseline (per query).

Usage (examples):
  python scripts/vector_index_tuner.py --dsn "$DATABASE_URL"
  python scripts/vector_index_tuner.py --mode auto --samples 25 --top-k 10
  python scripts/vector_index_tuner.py --mode hnsw --values 16,32,64,128,256

Notes:
- This tuner is non-destructive. It does not rebuild indexes.
- Ensure pgvector is installed and your table/column exist.
- Table layout assumed: doc_embeddings(embedding vector, id ...).
- You can customize table/column via flags.
"""
from __future__ import annotations

import argparse
import os
import random
import statistics
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import psycopg2
import psycopg2.extras

DEFAULT_VALUES_HNSW = [16, 32, 64, 128, 256]
DEFAULT_VALUES_IVF = [1, 4, 8, 16, 32, 64]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="pgvector index tuning helper")
    p.add_argument("--dsn", default=os.getenv("DATABASE_URL"), help="Postgres DSN (DATABASE_URL)")
    p.add_argument("--table", default=os.getenv("RAG_TABLE", "doc_embeddings"), help="Table name")
    p.add_argument("--col", default=os.getenv("RAG_COL", "embedding"), help="Vector column name")
    p.add_argument("--id-col", default=os.getenv("RAG_ID_COL", "id"), help="ID column name")
    p.add_argument("--mode", choices=["auto", "hnsw", "ivfflat"], default="auto", help="Index type to tune")
    p.add_argument("--top-k", type=int, default=int(os.getenv("RAG_TOP_K", "10")), help="Top-K per query")
    p.add_argument("--samples", type=int, default=20, help="Number of sample query vectors")
    p.add_argument("--values", default="", help="Comma-separated values for the knob (overrides defaults)")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for sampling")
    p.add_argument("--baseline-mult", type=int, default=4, help="Baseline multiplier (bigger = closer to max)")
    return p.parse_args()


def get_index_type(conn, table: str, col: str) -> Optional[str]:
    """Return 'hnsw' | 'ivfflat' | None based on index definition for table/column."""
    sql = """
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = ANY(current_schemas(true))
      AND tablename = %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (table,))
        rows = cur.fetchall()
    for r in rows:
        idxdef = r["indexdef"] or ""
        if f"USING hnsw" in idxdef and f"({col}" in idxdef:
            return "hnsw"
        if f"USING ivfflat" in idxdef and f"({col}" in idxdef:
            return "ivfflat"
    return None


def sample_query_vectors(conn, table: str, col: str, n: int) -> List[List[float]]:
    sql = f"SELECT {col} FROM {table} ORDER BY random() LIMIT %s"  # nosec B608
    with conn.cursor() as cur:
        cur.execute(sql, (n,))
        rows = cur.fetchall()
    # Each row[0] should be a vector; psycopg2 returns as list[float] when pgvector is installed
    return [list(row[0]) if not isinstance(row[0], list) else row[0] for row in rows]


def run_query(
    conn,
    table: str,
    id_col: str,
    col: str,
    vec: Sequence[float],
    top_k: int,
) -> Tuple[List[Any], float]:
    sql = (
        f"SELECT {id_col} FROM {table} ORDER BY {col} <-> %s LIMIT %s"  # nosec B608
    )
    t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql, (list(vec), top_k))
        ids = [r[0] for r in cur.fetchall()]
    dur_ms = (time.perf_counter() - t0) * 1000.0
    return ids, dur_ms


def set_runtime_knob(conn, mode: str, value: int) -> None:
    with conn.cursor() as cur:
        if mode == "hnsw":
            cur.execute("SET hnsw.ef_search = %s", (value,))
        elif mode == "ivfflat":
            cur.execute("SET ivfflat.probes = %s", (value,))
    conn.commit()


def tune(conn, mode: str, table: str, id_col: str, col: str, top_k: int, samples: int, values: List[int], baseline_mult: int) -> Dict[str, Any]:
    # Prepare queries
    qvecs = sample_query_vectors(conn, table, col, samples)
    if not qvecs:
        raise RuntimeError("No vectors found to sample; ensure table has data.")

    # Baseline value (rough max) for overlap metric
    baseline_value = max(values) * max(1, baseline_mult)
    set_runtime_knob(conn, mode, baseline_value)
    baseline_results: List[List[Any]] = []
    for v in qvecs:
        ids, _ = run_query(conn, table, id_col, col, v, top_k)
        baseline_results.append(ids)

    report: Dict[str, Any] = {"mode": mode, "top_k": top_k, "samples": samples, "results": []}

    for val in values:
        set_runtime_knob(conn, mode, val)
        latencies: List[float] = []
        overlaps: List[float] = []
        for i, v in enumerate(qvecs):
            ids, ms = run_query(conn, table, id_col, col, v, top_k)
            latencies.append(ms)
            # overlap recall against baseline
            base = set(baseline_results[i])
            hits = sum(1 for x in ids if x in base)
            overlaps.append(hits / float(top_k))
        report["results"].append(
            {
                "value": val,
                "avg_ms": statistics.fmean(latencies),
                "p95_ms": percentile(latencies, 95),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "avg_overlap": statistics.fmean(overlaps),
            }
        )

    # Recommend by highest avg_overlap then lowest avg_ms
    best = sorted(report["results"], key=lambda r: (-r["avg_overlap"], r["avg_ms"]))[0]
    report["recommendation"] = {"value": best["value"], "reason": "max overlap then min latency"}
    return report


def percentile(data: Sequence[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return d0 + d1


def main() -> None:
    args = parse_args()
    if not args.dsn:
        raise SystemExit("--dsn or DATABASE_URL required")

    random.seed(args.seed)
    values: List[int]
    if args.values:
        values = [int(x.strip()) for x in args.values.split(",") if x.strip()]
    else:
        values = DEFAULT_VALUES_HNSW if args.mode in ("auto", "hnsw") else DEFAULT_VALUES_IVF

    with psycopg2.connect(args.dsn) as conn:
        # Ensure we have an index type when auto
        mode = args.mode
        if mode == "auto":
            idx_type = get_index_type(conn, args.table, args.col)
            if not idx_type:
                raise SystemExit("Could not detect index type (hnsw|ivfflat). Set --mode explicitly.")
            mode = idx_type
        print({"detected_mode": mode, "values": values})
        report = tune(
            conn,
            mode=mode,
            table=args.table,
            id_col=args.id_col,
            col=args.col,
            top_k=args.top_k,
            samples=args.samples,
            values=values,
            baseline_mult=args.baseline_mult,
        )
        print(report)


if __name__ == "__main__":
    main()
