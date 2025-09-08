"""Inference dashboard ticker endpoints.

Exposes recent inference events with probability translations suitable for a
dev dashboard marquee / ticker.

Probability translations:
  avg_prob = exp(avg_logprob)
  top1_pct = top1_prob * 100

Color / severity hints derived from decision + confidence metrics.
"""
from __future__ import annotations
import math, os
from typing import Any, List, Dict
from fastapi import APIRouter

try:  # optional dependency
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore

router = APIRouter(prefix="/inference", tags=["inference"])

_DSN = os.getenv("INFERENCE_PG_DSN") or os.getenv("FAMILY_PG_DSN") or os.getenv("PG_DSN")


def _status_color(decision: str, avg_prob: float, entropy: float) -> str:
    if decision in {"abstain", "retrieve"}:
        return "orange"
    if decision == "reflect":
        return "yellow"
    if avg_prob < 0.1 or entropy > 3.0:
        return "red"
    return "green"


@router.get("/ticker")
def inference_ticker(limit: int = 15) -> Dict[str, Any]:  # pragma: no cover - simple IO
    if not psycopg2 or not _DSN:
        return {"events": [], "available": False, "reason": "psycopg2_or_dsn_missing"}
    sql = """
        SELECT ts, model_name, decision, avg_logprob, entropy, top1_prob, latency_ms, prompt_tokens, completion_tokens
        FROM model_inference_events
        ORDER BY ts DESC LIMIT %s;
    """
    try:
        with psycopg2.connect(_DSN) as conn:  # type: ignore[arg-type]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore
                cur.execute(sql, (limit,))
                rows = list(cur.fetchall())
    except Exception as e:  # pragma: no cover - defensive
        return {"events": [], "available": False, "reason": str(e)}

    events: List[Dict[str, Any]] = []
    for r in rows:
        avg_lp = r.get("avg_logprob") or 0.0
        avg_prob = math.exp(avg_lp)
        top1_prob = r.get("top1_prob") or 0.0
        item = {
            "ts": r["ts"].isoformat() if r.get("ts") else None,
            "model": r.get("model_name"),
            "decision": r.get("decision"),
            "avg_logprob": avg_lp,
            "avg_prob": avg_prob,
            "top1_prob": top1_prob,
            "top1_pct": top1_prob * 100.0,
            "entropy": r.get("entropy"),
            "latency_ms": r.get("latency_ms"),
            "tokens": {
                "prompt": r.get("prompt_tokens"),
                "completion": r.get("completion_tokens"),
            },
        }
        item["color"] = _status_color(item["decision"], item["avg_prob"], item["entropy"])  # visual hint
        events.append(item)
    return {"events": events, "available": True}


@router.get("/realtime")
def inference_realtime(limit: int = 25) -> Dict[str, Any]:  # alias for ticker w/ larger default
    return inference_ticker(limit=limit)


def _fetch_aggregate(window: str) -> Dict[str, Any]:
    if not psycopg2 or not _DSN:
        return {"window": window, "available": False}
    # Aggregate over window relative to now
    sql = """
        SELECT model_name,
               count(*) AS events,
               avg(avg_logprob) AS avg_avg_logprob,
               avg(entropy) AS avg_entropy,
               avg(top1_prob) AS avg_top1_prob,
               avg(latency_ms) AS avg_latency_ms,
               sum(prompt_tokens) AS total_prompt_tokens,
               sum(completion_tokens) AS total_completion_tokens,
               decision
        FROM model_inference_events
        WHERE ts > now() - ($$WIN$$)::interval
        GROUP BY model_name, decision;
    """.replace("$$WIN$$", window)
    dist: Dict[str, Dict[str, Any]] = {}
    try:
        with psycopg2.connect(_DSN) as conn:  # type: ignore[arg-type]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore
                cur.execute(sql)
                rows = cur.fetchall()
    except Exception as e:  # pragma: no cover
        return {"window": window, "available": False, "error": str(e)}
    for r in rows:
        model = r["model_name"]
        decision = r["decision"]
        bucket = dist.setdefault(model, {
            "model": model,
            "events": 0,
            "avg_avg_logprob": 0.0,
            "avg_entropy": 0.0,
            "avg_top1_prob": 0.0,
            "avg_latency_ms": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "decisions": {},
        })
        bucket["events"] += int(r["events"])  # type: ignore[arg-type]
        # Weighted running averages
        ev = max(1, int(r["events"]))
        for ksrc, kdst in [
            ("avg_avg_logprob", "avg_avg_logprob"),
            ("avg_entropy", "avg_entropy"),
            ("avg_top1_prob", "avg_top1_prob"),
            ("avg_latency_ms", "avg_latency_ms"),
        ]:
            cur_val = bucket[kdst]
            bucket[kdst] = (cur_val * (bucket["events"] - ev) + (r[ksrc] or 0.0) * ev) / bucket["events"]
        bucket["total_prompt_tokens"] += int(r["total_prompt_tokens"])  # type: ignore[arg-type]
        bucket["total_completion_tokens"] += int(r["total_completion_tokens"])  # type: ignore[arg-type]
        bucket["decisions"][decision] = bucket["decisions"].get(decision, 0) + ev
    # Final probability translation per model
    for b in dist.values():
        b["avg_prob"] = math.exp(b["avg_avg_logprob"]) if b["avg_avg_logprob"] is not None else 0.0
    return {"window": window, "available": True, "models": list(dist.values())}


@router.get("/aggregate")
def inference_aggregate(windows: str = "1 hour,24 hours") -> Dict[str, Any]:  # pragma: no cover - IO
    result = {"windows": []}
    for w in [w.strip() for w in windows.split(',') if w.strip()]:
        result["windows"].append(_fetch_aggregate(w))
    return result
