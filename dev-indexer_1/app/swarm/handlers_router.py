from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover
    try:
        import redis  # type: ignore
    except Exception:
        redis = None  # type: ignore

try:
    from app.rag.embedder import Embedder  # type: ignore
except Exception:  # pragma: no cover
    class Embedder:  # type: ignore
        def embed(self, _text: str) -> List[float]:
            return []
        def embed_batch(self, texts: List[str]) -> List[List[float]]:
            return [[] for _ in texts]

try:
    from sklearn.linear_model import LogisticRegression  # type: ignore
    from sklearn.preprocessing import StandardScaler  # type: ignore
    from sklearn.pipeline import make_pipeline  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    LogisticRegression = None  # type: ignore
    StandardScaler = None  # type: ignore
    make_pipeline = None  # type: ignore
    np = None  # type: ignore

import msgpack

router = APIRouter(prefix="/swarm/handlers", tags=["swarm-handlers"])


# Data models
class RegisterIn(BaseModel):
    name: str = Field(..., description="Handler name/id")
    description: Optional[str] = None


class ExampleIn(BaseModel):
    name: str
    text: str
    label: str


class TrainIn(BaseModel):
    name: str
    C: float = 1.0
    max_iter: int = 200


class PredictIn(BaseModel):
    name: str
    text: str


class ResetIn(BaseModel):
    name: str


# Redis helpers

def _redis():
    if redis is None:
        raise RuntimeError("redis client not installed")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port)


def _k(prefix: str, name: str) -> str:
    return f"swarm:handlers:{prefix}:{name}"


async def _get(r, key: str) -> Optional[bytes]:
    try:
        return await r.get(key)
    except Exception:
        return None


async def _set(r, key: str, val: bytes | bytearray) -> None:
    try:
        await r.set(key, bytes(val))
    except Exception:
        pass


# API endpoints
@router.post("/register")
async def register(payload: RegisterIn) -> Dict[str, Any]:
    r = _redis()
    info = {"name": payload.name, "description": payload.description}
    packed = msgpack.packb(info, use_bin_type=True)
    await _set(r, _k("info", payload.name), packed if packed is not None else b"")
    return {"ok": True, "name": payload.name}


@router.post("/example")
async def add_example(payload: ExampleIn) -> Dict[str, Any]:
    r = _redis()
    key = _k("examples", payload.name)
    raw = await _get(r, key)
    items: List[tuple[str, str]] = []
    if raw:
        try:
            items = msgpack.unpackb(raw, raw=False)
        except Exception:
            items = []
    items.append((payload.text, payload.label))
    packed = msgpack.packb(items, use_bin_type=True)
    await _set(r, key, packed if packed is not None else b"")
    return {"ok": True, "count": len(items)}


@router.post("/train")
async def train(payload: TrainIn) -> Dict[str, Any]:
    if LogisticRegression is None or np is None or make_pipeline is None or StandardScaler is None:
        raise HTTPException(status_code=503, detail="trainer unavailable (missing sklearn/numpy)")
    # Help type checker
    assert LogisticRegression is not None and np is not None and make_pipeline is not None and StandardScaler is not None
    r = _redis()
    raw = await _get(r, _k("examples", payload.name))
    if not raw:
        raise HTTPException(status_code=400, detail="no examples")
    try:
        items: List[tuple[str, str]] = msgpack.unpackb(raw, raw=False)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid examples store")
    texts = [t for t, _ in items]
    labels = [y for _, y in items]
    emb = Embedder()
    X = np.array(emb.embed_batch(texts), dtype=float)
    if X.size == 0:
        raise HTTPException(status_code=500, detail="embedding unavailable")
    clf = make_pipeline(StandardScaler(with_mean=False), LogisticRegression(C=payload.C, max_iter=payload.max_iter))
    clf.fit(X, labels)
    # Persist model via msgpack (using sklearn's get_params/meta only; not full pickle)
    # For simplicity, re-embed label centroids as prototype vectors (prototypical nn), also store labels list
    uniq = sorted(set(labels))
    centroids = {}
    for u in uniq:
        idx = [i for i, y in enumerate(labels) if y == u]
        if idx:
            centroids[u] = X[idx].mean(axis=0).tolist()
    packed = msgpack.packb({"labels": uniq, "centroids": centroids}, use_bin_type=True)
    await _set(r, _k("model", payload.name), packed if packed is not None else b"")
    return {"ok": True, "labels": uniq, "examples": len(items)}


@router.post("/predict")
async def predict(payload: PredictIn) -> Dict[str, Any]:
    r = _redis()
    raw = await _get(r, _k("model", payload.name))
    if not raw:
        raise HTTPException(status_code=404, detail="model not found")
    try:
        obj = msgpack.unpackb(raw, raw=False)
    except Exception:
        raise HTTPException(status_code=500, detail="invalid model blob")
    labels: List[str] = obj.get("labels", [])
    centroids: Dict[str, List[float]] = obj.get("centroids", {})
    if not labels or not centroids:
        raise HTTPException(status_code=500, detail="empty model")
    emb = Embedder()
    v = emb.embed(payload.text)
    # nearest centroid
    best_label = None
    best_dist = None
    for lab, c in centroids.items():
        if not c:
            continue
        d = sum((a - b) * (a - b) for a, b in zip(v, c))
        if best_dist is None or d < best_dist:
            best_label = lab
            best_dist = d
    return {"ok": True, "label": best_label, "distance": best_dist}


@router.get("/info")
async def info(name: str) -> Dict[str, Any]:
    r = _redis()
    raw = await _get(r, _k("info", name))
    meta = None
    if raw:
        try:
            meta = msgpack.unpackb(raw, raw=False)
        except Exception:
            meta = None
    return {"ok": True, "name": name, "meta": meta}


@router.post("/reset")
async def reset(payload: ResetIn) -> Dict[str, Any]:
    r = _redis()
    p1 = msgpack.packb([], use_bin_type=True)
    p2 = msgpack.packb({}, use_bin_type=True)
    await _set(r, _k("examples", payload.name), p1 if p1 is not None else b"")
    await _set(r, _k("model", payload.name), p2 if p2 is not None else b"")
    return {"ok": True}
