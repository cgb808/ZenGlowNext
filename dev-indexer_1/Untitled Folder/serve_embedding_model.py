#!/usr/bin/env python
"""FastAPI service to expose a (base or fine‑tuned / quantized) SentenceTransformer embedding model.

Endpoint:
  POST /embed {"inputs": ["text1", "text2", ...]}
Response:
  {"embeddings": [[...],[...],...], "model": name, "dim": n}

Also exposes:
  GET /healthz   -> {status, model}
  GET /info      -> {model, device, dim, quantized}
  GET /metrics   -> basic operational counters & latency aggregates

Features:
  - Works with models produced by fine_tuning/training/scripts/train_embedding_model.py
  - Works with quantized (int8/int4) models produced by quantize_embedding_model.py (loaded transparently)
  - Optional normalization (cosine-ready) with --normalize
  - Configurable concurrency semaphore (--concurrency) to backpressure large parallel loads
  - Batch size control passed to SentenceTransformer.encode
  - Graceful CUDA fallback if unavailable

Example:
  python scripts/serve_embedding_model.py --model models/bge-small-finetuned --port 8080 --normalize

Environment helpers (override CLI):
  SERVE_MODEL, SERVE_HOST, SERVE_PORT, SERVE_DEVICE, SERVE_CONCURRENCY, SERVE_BATCH_SIZE, SERVE_NORMALIZE=1
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:  # pragma: no cover - runtime guard
    raise SystemExit("Install training requirements (requirements-train.txt) to serve model.") from e

# ------------------------ FastAPI App & Models ------------------------
app = FastAPI()

class EmbedRequest(BaseModel):
    inputs: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dim: int

# ------------------------ Globals ------------------------
model: Optional[SentenceTransformer] = None
model_name: str = ''
model_dim: int = 0
sem: Optional[asyncio.Semaphore] = None
encode_batch_size: int = 32
normalize_embeddings: bool = False

# metrics
total_requests = 0
total_texts = 0
total_latency_sec = 0.0
max_latency_sec = 0.0
_metrics_lock = asyncio.Lock()


# ------------------------ Routes ------------------------
@app.post('/embed', response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    global total_requests, total_texts, total_latency_sec, max_latency_sec
    if model is None:
        raise HTTPException(503, 'model not loaded')
    if not req.inputs:
        return EmbedResponse(embeddings=[], model=model_name, dim=model_dim)
    start = time.perf_counter()
    if sem:
        async with sem:
            resp = await _embed(req.inputs)
    else:
        resp = await _embed(req.inputs)
    elapsed = time.perf_counter() - start
    async with _metrics_lock:
        total_requests += 1
        total_texts += len(req.inputs)
        total_latency_sec += elapsed
        if elapsed > max_latency_sec:
            max_latency_sec = elapsed
    return resp


async def _embed(texts: List[str]) -> EmbedResponse:
    loop = asyncio.get_event_loop()
    # run blocking encode in thread pool
    embs = await loop.run_in_executor(None, lambda: model.encode(texts, batch_size=encode_batch_size, normalize_embeddings=normalize_embeddings))  # type: ignore[arg-type]
    embs_list = embs.tolist()
    return EmbedResponse(embeddings=embs_list, model=model_name, dim=model_dim)


@app.get('/healthz')
async def health():
    return {'status': 'ok', 'model': model_name, 'dim': model_dim}


@app.get('/info')
async def info():
    device = None
    if model is not None:
        try:
            device = str(next(model._first_module().parameters()).device)
        except Exception:  # pragma: no cover - defensive
            device = 'unknown'
    quantized = False
    if model is not None:
        # heuristic: bitsandbytes quantization modules may appear in module names
        quantized = any('bnb' in type(m).__name__.lower() or 'int8' in type(m).__name__.lower() for m in model._first_module().modules())  # type: ignore[attr-defined]
    return {'model': model_name, 'device': device, 'dim': model_dim, 'quantized': quantized, 'normalize': normalize_embeddings, 'batch_size': encode_batch_size}


@app.get('/metrics')
async def metrics():
    async with _metrics_lock:
        avg_latency = (total_latency_sec / total_requests) if total_requests else 0.0
        return {
            'total_requests': total_requests,
            'total_texts': total_texts,
            'avg_latency_ms': avg_latency * 1000.0,
            'max_latency_ms': max_latency_sec * 1000.0,
        }


# ------------------------ Loading ------------------------
def load_model(path: str, device: str):
    global model, model_name, model_dim
    start = time.time()
    model = SentenceTransformer(path, device=device)
    model_name = path
    # derive dimension from first encode of a small constant vector token if needed
    try:
        emb = model.encode(['dimension_probe'], batch_size=1)
        model_dim = int(getattr(emb, 'shape', [0, 0])[1]) if hasattr(emb, 'shape') else len(emb[0])  # type: ignore[index]
    except Exception:  # pragma: no cover - defensive
        model_dim = 0
    dur = time.time() - start
    print(f'[info] model loaded in {dur:.2f}s on {device} (dim={model_dim})')


# ------------------------ Main ------------------------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default=os.environ.get('SERVE_MODEL'), required=not bool(os.environ.get('SERVE_MODEL')))
    parser.add_argument('--host', default=os.environ.get('SERVE_HOST', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('SERVE_PORT', '8000')))
    parser.add_argument('--device', default=os.environ.get('SERVE_DEVICE') or ('cuda' if os.environ.get('USE_CUDA','1') == '1' else 'cpu'))
    parser.add_argument('--concurrency', type=int, default=int(os.environ.get('SERVE_CONCURRENCY', '4')))
    parser.add_argument('--batch-size', type=int, default=int(os.environ.get('SERVE_BATCH_SIZE', '32')))
    parser.add_argument('--normalize', action='store_true', default=os.environ.get('SERVE_NORMALIZE','0') == '1')
    parser.add_argument('--reload', action='store_true', help='Enable autoreload (dev only)')
    return parser.parse_args()


def main():  # pragma: no cover - entry point
    global sem, encode_batch_size, normalize_embeddings
    args = parse_args()

    if args.device.startswith('cuda'):
        try:
            import torch  # noqa: F401
            if not torch.cuda.is_available():  # type: ignore[attr-defined]
                print('[warn] cuda requested but not available; falling back to cpu')
                args.device = 'cpu'
        except Exception:
            print('[warn] torch not available; forcing cpu')
            args.device = 'cpu'

    load_model(args.model, args.device)
    sem = asyncio.Semaphore(args.concurrency) if args.concurrency > 0 else None
    encode_batch_size = args.batch_size
    normalize_embeddings = args.normalize

    # graceful shutdown logging
    def _handle_sig(sig, frame):  # pragma: no cover - signal hook
        print(f'[info] received {sig.name}; shutting down')
        raise SystemExit(0)
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level='info',
    )


if __name__ == '__main__':  # pragma: no cover
    main()
