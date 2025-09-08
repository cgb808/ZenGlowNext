from __future__ import annotations
import uuid, math, time, json
from typing import Iterable, List, Tuple, Optional, Dict, Any

try:  # optional
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore


def _entropy(logprobs: List[float]) -> float:
    # logprobs = log p_i ; entropy = -sum p_i log p_i ; if only 1 top token provided, entropy ~0
    ps = [math.exp(lp) for lp in logprobs]
    s = sum(ps)
    if s <= 0:
        return 0.0
    norm = [p / s for p in ps]
    return float(-sum(p * math.log(p + 1e-12) for p in norm))


def compute_metrics(token_logprobs: List[Tuple[str, float]]) -> Dict[str, float]:
    if not token_logprobs:
        return {"avg_logprob": 0.0, "entropy": 0.0, "top1_prob": 0.0}
    lps = [lp for _, lp in token_logprobs]
    avg_lp = sum(lps) / len(lps)
    # approximate top1 prob from first token only (heuristic if not full distribution)
    top1_prob = math.exp(token_logprobs[0][1]) if token_logprobs else 0.0
    ent = _entropy(lps[: min(8, len(lps))])  # small window
    return {"avg_logprob": float(avg_lp), "entropy": float(ent), "top1_prob": float(top1_prob)}


def log_inference_event(
    dsn: str,
    model_name: str,
    user_id: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    token_logprobs: List[Tuple[str, float]],  # sequence token -> logprob (generated only)
    decision: str,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist inference event + per-token stats.

    decision: proceed|abstain|reflect|retrieve
    """
    if not psycopg2:  # pragma: no cover
        return ""  # silently skip if driver absent
    metrics = compute_metrics(token_logprobs)
    eid = str(uuid.uuid4())
    meta_json = json.dumps(meta or {})
    sql_event = """
        INSERT INTO model_inference_events
        (id, model_name, user_id, prompt_tokens, completion_tokens, latency_ms, avg_logprob, entropy, top1_prob, decision, meta)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """
    sql_token = """
        INSERT INTO model_inference_token_stats (event_id, position, token, logprob, is_generated)
        VALUES (%s,%s,%s,%s,TRUE);
    """
    with psycopg2.connect(dsn) as conn:  # type: ignore
        with conn.cursor() as cur:
            cur.execute(
                sql_event,
                (
                    eid,
                    model_name,
                    user_id,
                    prompt_tokens,
                    completion_tokens,
                    latency_ms,
                    metrics["avg_logprob"],
                    metrics["entropy"],
                    metrics["top1_prob"],
                    decision,
                    meta_json,
                ),
            )
            for idx, (tok, lp) in enumerate(token_logprobs):
                cur.execute(sql_token, (eid, idx, tok, lp))
    return eid
