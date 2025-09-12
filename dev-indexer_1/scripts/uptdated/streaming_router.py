"""Streaming Diff API Scaffold (Artifact D)

Server-Sent Events (SSE) endpoint that emits phased ranking data for a RAG query.

Phases:
  P0: Provisional similarity-based candidate list (raw ANN / pgvector search + optional memory weighted merge)
  P1: LTR-scored ordering (uses GLOBAL_LTR_MODEL over assembled features)
  P2: Simulated contextual adjustments (deterministic scoring deltas)

Event Format (SSE lines):
  data: {"phase": "P0|P1|P2", "provisional": bool, "results": [...], optional extras}

Future Enhancements (not implemented yet):
  * Real index routing (HNSW vs IVFFLAT) once dual indexes exist
  * True memory/source blending using chunk_features / engagement stats
  * LM-based contextual rescoring / diversification
  * Delta emission (only changed ranks) instead of full result sets
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .db_client import DBClient
from .embedder import Embedder
from .feature_assembler import Candidate, assemble_features
from .ltr import GLOBAL_LTR_MODEL

router = APIRouter(prefix="/rag", tags=["rag-stream"])

_embedder = Embedder()


class StreamQueryPayload(BaseModel):
    query: str
    top_k: int | None = None
    user_id: int | None = None
    group_ids: List[int] | None = None


def _ann_search(
    embedding: List[float],
    top_k: int,
    query_text: str,
    table: str = "doc_embeddings",
    sources: Optional[List[str]] = None,
    exclude_sources: Optional[List[str]] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Minimal ANN search wrapper (pgvector) with basic source filtering.

    Returns (hits, meta). Each hit: {id, text, distance, source?}
    """
    meta: Dict[str, Any] = {"table": table}
    try:
        db = DBClient()
        hits_raw = db.vector_search(embedding, top_k=top_k)
        # db client returns: id, text, metadata, distance
        hits: List[Dict[str, Any]] = []
        for h in hits_raw:
            m = h.get("metadata") or {}
            src = m.get("source") if isinstance(m, dict) else None
            if sources and (src not in sources):
                continue
            if exclude_sources and src in exclude_sources:
                continue
            hits.append(
                {
                    "id": h.get("id"),
                    "text": h.get("text") or "",
                    "distance": h.get("distance", 0.0),
                    "source": src,
                }
            )
        meta["retrieved"] = len(hits)
        return hits, meta
    except Exception as e:  # graceful degradation
        meta["error"] = str(e)
        return [], meta
    finally:
        try:
            db.close()  # type: ignore
        except Exception:
            pass


def _choose_index(embedding: List[float], query_text: str) -> str:
    """Stub for dual-index routing (future): returns which ANN index to use.

    Heuristic placeholder: if query length < 40 chars => 'hnsw', else 'ivfflat'.
    Later will incorporate latency feedback + config in ann_runtime_config table.
    """
    return "hnsw" if len(query_text) < 40 else "ivfflat"


def _embed_texts(texts: List[str]) -> List[List[float]]:
    return _embedder.embed_batch(texts)


async def _iter_events(payload: StreamQueryPayload) -> AsyncGenerator[str, None]:
    if not payload.query.strip():
        yield "event: error\n" + 'data: {"error":"empty query"}\n\n'
        return

    # Wake-style memory capture: "hey jarvice remember this" prefix stores the remainder as a memory chunk.
    lower_q = payload.query.lower().strip()
    mem_prefixes = [
        "hey jarvice remember this",
        "hey jarvice remember",
        "jarvice remember this",
        "jarvice remember",
    ]
    for pref in mem_prefixes:
        if lower_q.startswith(pref):
            remainder = payload.query[len(pref) :].strip(" :,-")
            if remainder:
                emb = _embed_texts([remainder])[0]
                stored_id: Optional[int] = None
                try:
                    db = DBClient()
                    with db.conn.cursor() as cur:  # type: ignore
                        cur.execute(
                            """
                            INSERT INTO doc_embeddings (source, chunk, embedding, metadata)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                "memory",
                                remainder,
                                emb,
                                json.dumps(
                                    {
                                        "source": "memory",
                                        "wake": True,
                                        "user_id": payload.user_id,
                                        "group_ids": payload.group_ids,
                                    }
                                ),
                            ),
                        )
                        row = cur.fetchone()
                        if row:
                            stored_id = row[0]
                except Exception as e:
                    yield "data: " + json.dumps(
                        {
                            "phase": "MEM",
                            "ack": False,
                            "error": str(e),
                            "text_preview": remainder[:160],
                            "user_id": payload.user_id,
                        }
                    ) + "\n\n"
                    return
                finally:
                    try:
                        db.close()  # type: ignore
                    except Exception:
                        pass
                yield "data: " + json.dumps(
                    {
                        "phase": "MEM",
                        "ack": True,
                        "stored_id": stored_id,
                        "text_preview": remainder[:160],
                        "source": "memory",
                        "user_id": payload.user_id,
                        "group_ids": payload.group_ids,
                    }
                ) + "\n\n"
                return
            else:
                yield "data: " + json.dumps(
                    {"phase": "MEM", "ack": False, "error": "no content"}
                ) + "\n\n"
                return

    top_k = payload.top_k or int(os.getenv("RAG_TOP_K_DEFAULT", "10"))
    t_embed_start = time.time()
    q_vec = _embed_texts([payload.query])[0]
    embed_ms = int((time.time() - t_embed_start) * 1000)

    # ---- Phase P0 ----
    enable_memory = os.getenv("RAG_ENABLE_MEMORY", "0") in ("1", "true", "True")
    memory_weight = float(os.getenv("RAG_MEMORY_WEIGHT", "0.85"))
    mem_top = int(os.getenv("RAG_MEMORY_TOP_K", str(max(1, top_k // 2))))

    base_hits, meta = _ann_search(
        q_vec, top_k, payload.query, table="doc_embeddings", exclude_sources=["memory"]
    )
    meta["index"] = _choose_index(q_vec, payload.query)
    raw_hits = list(base_hits)
    if enable_memory:
        mem_hits, meta_mem = _ann_search(
            q_vec, mem_top, payload.query, table="doc_embeddings", sources=["memory"]
        )
        for mh in mem_hits:
            mh["distance"] *= memory_weight  # down-weight distance (closer)
        raw_hits.extend(mem_hits)
        meta["memory"] = {"added": len(mem_hits), "weight": memory_weight}

    # Deduplicate by id taking lowest distance
    best_by_id: Dict[Any, Dict[str, Any]] = {}
    for h in raw_hits:
        cid = h["id"]
        if cid is None:
            continue
        if cid not in best_by_id or h["distance"] < best_by_id[cid]["distance"]:
            best_by_id[cid] = h
    raw_hits = list(best_by_id.values())
    raw_hits.sort(key=lambda x: x["distance"])  # ascending distance
    raw_hits = raw_hits[:top_k]
    p0_results = [
        {
            "id": h["id"],
            "text_preview": (h["text"] or "")[:160],
            "distance": h["distance"],
        }
        for h in raw_hits
    ]
    ev0 = {
        "phase": "P0",
        "provisional": True,
        "results": p0_results,
        "meta": {**meta, "embed_ms": embed_ms},
    }
    yield "data: " + json.dumps(ev0) + "\n\n"
    await asyncio.sleep(0)  # cooperative yield

    # ---- Phase P1 (LTR) ----
    t_ltr_start = time.time()
    candidates = [
        Candidate(
            chunk_id=h["id"],
            text=h["text"],
            distance=h["distance"],
            source=h.get("source"),
        )
        for h in raw_hits
    ]
    feats, names = assemble_features(payload.query, candidates)
    scores = GLOBAL_LTR_MODEL.score_matrix(feats)
    enriched = []
    for c, s in zip(candidates, scores):
        enriched.append(
            {
                "id": c.chunk_id,
                "score": s,
                "distance": c.distance,
                "text_preview": c.text[:160],
            }
        )
    enriched.sort(key=lambda x: x["score"], reverse=True)
    ltr_ms = int((time.time() - t_ltr_start) * 1000)
    # Build delta vs P0 ordering
    p0_rank = {r["id"]: i for i, r in enumerate(p0_results)}
    deltas_p1: List[Dict[str, Any]] = []
    for i, r in enumerate(enriched):
        old = p0_rank.get(r["id"])
        if old is None:
            deltas_p1.append(
                {"id": r["id"], "change": "new", "new_rank": i, "score": r["score"]}
            )
        else:
            if old != i:
                deltas_p1.append(
                    {
                        "id": r["id"],
                        "old_rank": old,
                        "new_rank": i,
                        "rank_delta": old - i,
                        "score": r["score"],
                    }
                )
    ev1 = {
        "phase": "P1",
        "provisional": False,
        "feature_names": names,
        "delta": deltas_p1,
        "ltr_ms": ltr_ms,
        "result_count": len(enriched),
    }
    yield "data: " + json.dumps(ev1) + "\n\n"

    # ---- Phase P2 (Contextual Adjustments - simulated) ----
    timeout_ms = int(os.getenv("LM_REFINEMENT_TIMEOUT_MS", "300"))
    await asyncio.sleep(min(timeout_ms / 1000.0, 0.3))
    # Contextual heuristic: token overlap boost
    q_tokens = {t for t in payload.query.lower().split() if t}
    adjusted = list(enriched)
    for r in adjusted:
        text_tokens = set((r.get("text_preview") or "").lower().split())
        overlap = len(q_tokens & text_tokens)
        if overlap:
            r["score"] += 0.03 * overlap
    # Deterministic positional tweak (same as before) layered on top
    for i, r in enumerate(adjusted):
        additive = 0.0
        if i == 0:
            additive = 0.05 * (r["score"] if r["score"] else 1.0)
        elif i > 5:
            additive = -0.02 * (r["score"] if r["score"] else 1.0)
        if additive:
            r["score"] += additive
            r["score_delta"] = r.get("score_delta", 0.0) + additive
    # Re-rank after adjustments
    adjusted.sort(key=lambda x: x["score"], reverse=True)
    # Delta vs P1
    p1_rank = {r["id"]: i for i, r in enumerate(enriched)}
    deltas_p2: List[Dict[str, Any]] = []
    for i, r in enumerate(adjusted):
        old = p1_rank.get(r["id"])
        if old is None:
            deltas_p2.append(
                {"id": r["id"], "change": "new", "new_rank": i, "score": r["score"]}
            )
        else:
            if old != i or r.get("score_delta"):
                deltas_p2.append(
                    {
                        "id": r["id"],
                        "old_rank": old,
                        "new_rank": i,
                        "rank_delta": old - i,
                        "score": r["score"],
                        "score_delta": r.get("score_delta"),
                    }
                )
    ev2 = {
        "phase": "P2",
        "provisional": False,
        "delta": deltas_p2,
        "final": True,
        "result_count": len(adjusted),
    }
    yield "data: " + json.dumps(ev2) + "\n\n"


@router.post("/stream_query")
async def stream_query(payload: StreamQueryPayload):
    return StreamingResponse(_iter_events(payload), media_type="text/event-stream")
