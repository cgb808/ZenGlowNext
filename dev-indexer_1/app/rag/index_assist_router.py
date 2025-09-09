from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from app.rag.embedder import Embedder  # type: ignore
except Exception:  # pragma: no cover
    class Embedder:  # type: ignore
        def embed(self, _text: str) -> List[float]:
            return []
        def embed_batch(self, texts: List[str]) -> List[List[float]]:
            return [[] for _ in texts]

try:
    from app.rag.db_client import DBClient  # type: ignore
except Exception:  # pragma: no cover
    class DBClient:  # type: ignore
        def __init__(self) -> None:
            self.conn = None
        def close(self) -> None:
            return None
        def upsert_doc_embedding(self, source: str, chunk: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
            return None

router = APIRouter(prefix="/rag/assist", tags=["rag-assist"])


class IndexIn(BaseModel):
    source: str = Field(..., description="Logical source, e.g., 'edge-fn:xyz'")
    text: str
    metadata: Optional[Dict[str, Any]] = None


class CategorizeIn(BaseModel):
    text: str
    hint: Optional[str] = None


class CatalogIn(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    tags: List[str] = []
    meta: Optional[Dict[str, Any]] = None


def _cheap_categories(text: str, hint: Optional[str] = None) -> List[str]:
    # very lightweight heuristics; safe defaults
    t = (hint or "") + "\n" + text
    t = t.lower()
    cats: List[str] = []
    if any(k in t for k in ("sql", "query", "database")):
        cats.append("data")
    if any(k in t for k in ("python", "typescript", "react", "fastapi")):
        cats.append("code")
    if any(k in t for k in ("design", "ux", "ui")):
        cats.append("design")
    if "error" in t or "exception" in t:
        cats.append("incident")
    if not cats:
        cats.append("general")
    # keep unique order
    dedup: List[str] = []
    for c in cats:
        if c not in dedup:
            dedup.append(c)
    return dedup


def _ensure_tables(db: DBClient) -> None:
    # Minimal compatibility shim: ensure legacy doc_embeddings exists.
    if getattr(db, "conn", None) is None:
        return
    try:
        with db.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_embeddings (
                    id bigserial PRIMARY KEY,
                    source text,
                    chunk text NOT NULL,
                    embedding vector(384),
                    created_at timestamptz DEFAULT now(),
                    batch_tag text,
                    metadata jsonb
                );
                """
            )
    except Exception:
        # non-fatal; service continues
        pass


def _upsert_doc(db: DBClient, source: str, chunk: str, emb: List[float], metadata: Optional[Dict[str, Any]]) -> Optional[int]:
    if getattr(db, "conn", None) is None or not emb:
        return None
    try:
        with db.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                INSERT INTO doc_embeddings (source, chunk, embedding, metadata)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (source, chunk, emb, metadata),
            )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None
    except Exception as e:
        os.environ["INDEX_ASSIST_LAST_ERROR"] = str(e)
        return None


@router.post("/index")
def index(payload: IndexIn) -> Dict[str, Any]:
    try:
        embedder = Embedder()
        vec = embedder.embed(payload.text)
        with DBClient() as db:  # type: ignore[attr-defined]
            _ensure_tables(db)
            new_id = _upsert_doc(db, payload.source, payload.text, vec, payload.metadata)
        return {"ok": True, "id": new_id, "vec_dim": len(vec)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categorize")
def categorize(payload: CategorizeIn) -> Dict[str, Any]:
    cats = _cheap_categories(payload.text, payload.hint)
    return {"ok": True, "categories": cats}


@router.post("/catalog")
def catalog(payload: CatalogIn) -> Dict[str, Any]:
    # placeholder for writing into artifacts/documents tables in consolidated schema
    # keep it no-op for now, return echo and plan for DB write later
    return {"ok": True, "id": payload.id, "title": payload.title, "tags": payload.tags, "meta": payload.meta}
