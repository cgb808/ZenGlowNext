"""Ranking Pipeline Router (Artifact B)

Integrates:
  * Similarity search (current doc_embeddings table)
  * Feature assembly scaffold
  * LTR linear scoring

Provides /rag/query2 endpoint returning scored results with feature metadata.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List

import psycopg2  # type: ignore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.redis_cache import cache_get_msgpack  # type: ignore
from app.core.redis_cache import (cache_rag_query_result, cache_set_msgpack,
                                  get_cached_rag_query)

from .feature_assembler import (FEATURE_SCHEMA_VERSION, Candidate,
                                assemble_features)
from .ltr import GLOBAL_LTR_MODEL

try:
    from app.health.health_router import RAG_QUERY_COUNT  # type: ignore
    from app.health.health_router import RAG_QUERY_LATENCY
except Exception:  # pragma: no cover
    RAG_QUERY_COUNT = None
    RAG_QUERY_LATENCY = None

router = APIRouter(prefix="/rag", tags=["rag-advanced"])

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K_DEFAULT", "10"))
MAX_TOP_K = int(os.getenv("RAG_TOP_K_MAX", "200"))

# Fusion weight override / versioning (dynamic updates via endpoint)
_FUSION_WEIGHT_OVERRIDE: tuple[float, float] | None = (
    None  # (ltr, conceptual) raw values
)
_FUSION_WEIGHT_VERSION: int = 1


def get_current_fusion_weights() -> tuple[float, float, int]:
    """Return normalized (ltr, conceptual) weights + version.
    If override present use it, else derive from environment.
    Normalization ensures they sum to 1 (fallback 0.5/0.5 if invalid).
    """
    if _FUSION_WEIGHT_OVERRIDE is not None:
        ltr_raw, concept_raw = _FUSION_WEIGHT_OVERRIDE
    else:
        ltr_raw = float(os.getenv("RAG_FUSION_LTR_WEIGHT", "0.6"))
        concept_raw = float(os.getenv("RAG_FUSION_CONCEPTUAL_WEIGHT", "0.4"))
    total = ltr_raw + concept_raw
    if total <= 0:
        return 0.5, 0.5, _FUSION_WEIGHT_VERSION
    return ltr_raw / total, concept_raw / total, _FUSION_WEIGHT_VERSION


class Query2Payload(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(None, ge=1, le=MAX_TOP_K)


class FusionWeightsPayload(BaseModel):
    ltr: float = Field(..., description="LTR weight (non-negative)")
    conceptual: float = Field(..., description="Conceptual weight (non-negative)")


@router.get("/fusion/weights")
def get_fusion_weights() -> Dict[str, Any]:
    ltr, concept, version = get_current_fusion_weights()
    return {
        "weights": {"ltr": ltr, "conceptual": concept},
        "version": version,
        "override": _FUSION_WEIGHT_OVERRIDE is not None,
    }


@router.put("/fusion/weights")
def update_fusion_weights(payload: FusionWeightsPayload) -> Dict[str, Any]:
    global _FUSION_WEIGHT_OVERRIDE, _FUSION_WEIGHT_VERSION
    if payload.ltr < 0 or payload.conceptual < 0:
        raise HTTPException(400, "Weights must be non-negative")
    _FUSION_WEIGHT_OVERRIDE = (payload.ltr, payload.conceptual)
    _FUSION_WEIGHT_VERSION += 1
    ltr, concept, version = get_current_fusion_weights()
    return {
        "weights": {"ltr": ltr, "conceptual": concept},
        "version": version,
        "normalized": True,
    }


def _pg_connect():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(500, "DATABASE_URL not set")
    return psycopg2.connect(dsn)


def _embed_query(text: str) -> List[float]:
    # Placeholder: swap with Embedder directly to avoid main import cycle.
    from app.rag.embedder import Embedder  # local import to prevent circular

    emb = Embedder()
    return emb.embed(text)


def _similarity_search_pgvector(query_vec: List[float], k: int) -> List[Candidate]:
    sql = """
        SELECT id, chunk, embedding <-> %s::vector AS dist, source
        FROM doc_embeddings
        ORDER BY embedding <-> %s::vector
        LIMIT %s
        """
    try:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (query_vec, query_vec, k))
                rows = cur.fetchall()
    except Exception as e:  # graceful degradation
        logging.getLogger(__name__).warning(
            "retrieval_failed", extra={"event": "retrieval", "error": str(e)}
        )
        return []
    cands: List[Candidate] = []
    for r in rows:
        cands.append(
            Candidate(
                chunk_id=int(r[0]),
                text=r[1],
                distance=float(r[2]),
                source=r[3],
            )
        )
    return cands


def _similarity_search_supabase(
    query_vec: List[float], k: int
) -> List[Candidate]:  # pragma: no cover - stub
    # Placeholder for Supabase RPC-based retrieval; returns empty list for now.
    # Future: call postgrest RPC with embedding vector & limit.
    return []


FEATURE_CACHE_NS_PREFIX = "rag:features"  # namespace base
FEATURE_CACHE_TTL = int(os.getenv("RAG_FEATURE_CACHE_TTL", "60"))  # seconds


@router.post("/query2")
async def rag_query2(payload: Query2Payload) -> Dict[str, Any]:
    q = payload.query.strip()
    if not q:
        raise HTTPException(400, "Empty query")
    top_k = payload.top_k or DEFAULT_TOP_K

    # Determine current fusion weights early (dynamic override aware)
    cur_w_ltr, cur_w_concept, cur_w_version = get_current_fusion_weights()

    # Full response cache (only valid if weights unchanged)
    try:
        cached = get_cached_rag_query(q, top_k)
    except Exception:
        cached = None  # Redis unavailable; proceed without cache
    if cached:
        fw = cached.get("fusion_weights") if isinstance(cached, dict) else None
        cached_version = (
            cached.get("fusion_weights_version") if isinstance(cached, dict) else None
        )
        if (
            fw
            and cached_version == cur_w_version
            and abs(fw.get("ltr", -1) - cur_w_ltr) < 1e-9
            and abs(fw.get("conceptual", -1) - cur_w_concept) < 1e-9
        ):
            if RAG_QUERY_COUNT:
                try:
                    RAG_QUERY_COUNT.labels(endpoint="query2", cache_hit="full").inc()
                except Exception:
                    pass
            return cached  # weights match, safe reuse
        # else ignore and rebuild using feature cache if available

    # Feature-level cache: reuse candidate + feature matrix + ltr scores; recompute fusion with new weights
    feature_cache_key = q  # hashing handled by redis helper
    feature_ns = f"{FEATURE_CACHE_NS_PREFIX}:{top_k}"
    cached_features = None
    try:
        cached_features = cache_get_msgpack(feature_ns, feature_cache_key)
    except Exception:
        cached_features = None

    timer_start = time.perf_counter()
    embed_start = feature_start = ltr_start = fusion_start = None  # markers
    embed_ms = retrieve_ms = feature_ms = ltr_ms = fusion_ms = 0.0
    cache_hit_type = "none"
    retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", "pgvector").lower()
    if retrieval_mode == "disabled":
        # Skip embedding + retrieval entirely (dev mode)
        feature_names = ["concept_score_placeholder"]
        feature_matrix = []
        ltr_scores = []
        distances = []
        chunk_ids = []
        texts = []
        cache_hit_type = "disabled"
    elif cached_features:
        feature_names = cached_features.get("feature_names", [])
        raw_items = cached_features.get("items", [])
        candidates = []  # not needed for fusion recompute
        feature_matrix = [ri.get("features_vec", []) for ri in raw_items]
        ltr_scores = [ri.get("ltr_score", 0.0) for ri in raw_items]
        distances = [ri.get("distance", 0.0) for ri in raw_items]
        chunk_ids = [ri.get("chunk_id") for ri in raw_items]
        texts = [ri.get("text_preview", "") for ri in raw_items]
        cache_hit_type = "feature"
    else:
        embed_start = time.perf_counter()
        q_vec = _embed_query(q)
        embed_end = time.perf_counter()
        retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", "pgvector").lower()
        if retrieval_mode == "supabase_rpc":
            candidates = _similarity_search_supabase(q_vec, top_k)
        else:
            candidates = _similarity_search_pgvector(q_vec, top_k)
        retrieve_end = time.perf_counter()
        feature_start = retrieve_end
        feature_matrix, feature_names = assemble_features(q, candidates)
        feature_end = time.perf_counter()
        ltr_start = feature_end
        ltr_scores = GLOBAL_LTR_MODEL.score_matrix(feature_matrix)
        ltr_end = time.perf_counter()
        # compute stage durations
        embed_ms = (embed_end - embed_start) * 1000.0
        retrieve_ms = (retrieve_end - embed_end) * 1000.0
        feature_ms = (feature_end - feature_start) * 1000.0
        ltr_ms = (ltr_end - ltr_start) * 1000.0
        # Persist feature-level cache (store minimal fields)
        minimal_items = []
        for c, feats, ltr in zip(candidates, feature_matrix, ltr_scores):
            minimal_items.append(
                {
                    "chunk_id": c.chunk_id,
                    "text_preview": c.text[:300],
                    "distance": c.distance,
                    "features_vec": feats,
                    "ltr_score": ltr,
                }
            )
        try:
            cache_set_msgpack(
                feature_ns,
                feature_cache_key,
                {"feature_names": feature_names, "items": minimal_items},
                ttl_seconds=FEATURE_CACHE_TTL,
            )
        except Exception:
            pass
        distances = [c.distance for c in candidates]
        chunk_ids = [c.chunk_id for c in candidates]
        texts = [c.text for c in candidates]

    # Fusion weights (normalize if sum != 1)
    w_ltr, w_concept = cur_w_ltr, cur_w_concept

    # Derive conceptual score (currently distance-based similarity) & normalize LTR for fusion
    conceptual_scores = [feats[0] if feats else 0.0 for feats in feature_matrix]

    if ltr_scores:
        min_ltr = min(ltr_scores)
        max_ltr = max(ltr_scores)
        if max_ltr - min_ltr > 1e-9:
            ltr_scores_norm = [(s - min_ltr) / (max_ltr - min_ltr) for s in ltr_scores]
        else:
            ltr_scores_norm = [0.5] * len(ltr_scores)
    else:
        ltr_scores_norm = []

    enriched = []
    fusion_start = time.perf_counter()
    for idx, (ltr_raw, ltr_n, feats, concept) in enumerate(
        zip(ltr_scores, ltr_scores_norm, feature_matrix, conceptual_scores)
    ):
        chunk_id = chunk_ids[idx] if idx < len(chunk_ids) else None
        distance = distances[idx] if idx < len(distances) else None
        text_preview = texts[idx][:300] if idx < len(texts) else ""
        fused = w_ltr * ltr_n + w_concept * concept
        enriched.append(
            {
                "chunk_id": chunk_id,
                "text_preview": text_preview,
                "distance": distance,
                "ltr_score": ltr_raw,
                "conceptual_score": concept,
                "fused_score": fused,
                "features": {name: val for name, val in zip(feature_names, feats)},
            }
        )
    enriched.sort(key=lambda x: x["fused_score"], reverse=True)
    fusion_end = time.perf_counter()
    fusion_ms = (fusion_end - fusion_start) * 1000.0
    if RAG_QUERY_COUNT:
        try:
            RAG_QUERY_COUNT.labels(endpoint="query2", cache_hit=cache_hit_type).inc()
        except Exception:
            pass
    elapsed = time.perf_counter() - timer_start
    if RAG_QUERY_LATENCY:
        try:
            RAG_QUERY_LATENCY.observe(elapsed)
        except Exception:
            pass
    # Record lightweight stats
    try:
        from app.health.health_router import record_query_stats  # type: ignore

        record_query_stats(elapsed, cache_hit_type)
    except Exception:
        pass
    total_ms = (time.perf_counter() - timer_start) * 1000.0
    response = {
        "query": q,
        "top_k": top_k,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_names": feature_names,
        "fusion_weights": {"ltr": w_ltr, "conceptual": w_concept},
        "fusion_weights_version": cur_w_version,
        "results": enriched,
        # alias for frontend variants expecting 'items'
        "items": enriched,
        "scoring_version": 1,
        "timings": {
            "total_ms": total_ms,
            "embed_ms": embed_ms,
            "retrieve_ms": retrieve_ms,
            "feature_ms": feature_ms,
            "ltr_ms": ltr_ms,
            "fusion_ms": fusion_ms,
        },
        "retrieval_mode": os.getenv("RAG_RETRIEVAL_MODE", "pgvector").lower(),
    }
    try:
        cache_rag_query_result(q, top_k, response)
    except Exception:
        pass  # ignore cache store errors
    return response
