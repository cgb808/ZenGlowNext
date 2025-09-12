#!/usr/bin/env python
"""Lightweight embedding HTTP server (Option A) using raw HF AutoModel for quantized or base models.

Endpoints:
  POST /model/embed {"texts": [..], "normalize": bool?} -> {"embeddings": [...], "model": name, "dim": int}
  GET  /healthz -> {"status":"ok", "model": name, "dim": int}

Features:
  - Works with standard or bitsandbytes int8/int4 quantized models.
  - Mean pooling over last hidden state (CLS excluded) with attention mask.
  - Optional L2 normalization (cosine-ready) per request or default via EMBED_NORMALIZE=1.
  - Simple concurrency limit via semaphore EMBED_CONCURRENCY (default 4).
  - Minimal dependency surface (transformers, torch, fastapi, uvicorn).

Environment:
  HF_EMBED_MODEL=path_or_repo (required if --model omitted)
  EMBED_HOST=0.0.0.0
  EMBED_PORT=8090
  EMBED_DEVICE=cuda|cpu (auto if available)
  EMBED_BATCH=32
  EMBED_NORMALIZE=1|0
  EMBED_CONCURRENCY=4

Run example:
  python scripts/serve_hf_embed.py --model models/bge-func-ingest-int8 --port 8091 --normalize

Gateway integration:
  export EMBED_ENDPOINT=http://127.0.0.1:8091/model/embed
"""
from __future__ import annotations
import argparse, os, math, asyncio, time
from typing import List, Optional

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer
import uvicorn

app = FastAPI()

class EmbedPayload(BaseModel):
    texts: List[str]
    normalize: Optional[bool] = None

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dim: int
    count: int

_model = None
_tokenizer = None
_model_name = ''
_dim = 0
_semaphore: Optional[asyncio.Semaphore] = None
_default_normalize = True
_batch_size = 32
_device = 'cpu'

@torch.inference_mode()
def _encode_batch(texts: List[str], normalize: bool) -> List[List[float]]:
    tok = _tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors='pt')
    tok = {k: v.to(_device) for k, v in tok.items()}
    out = _model(**tok)
    last_hidden = out.last_hidden_state  # (bs, seq, dim)
    attn = tok['attention_mask'].unsqueeze(-1)  # (bs, seq, 1)
    summed = (last_hidden * attn).sum(dim=1)
    counts = attn.sum(dim=1).clamp(min=1)
    mean = summed / counts
    if normalize:
        mean = torch.nn.functional.normalize(mean, p=2, dim=1)
    return mean.cpu().tolist()

async def _embed(texts: List[str], normalize: bool) -> List[List[float]]:
    # Chunk into mini-batches for memory safety
    out: List[List[float]] = []
    for i in range(0, len(texts), _batch_size):
        chunk = texts[i:i+_batch_size]
        out.extend(_encode_batch(chunk, normalize))
    return out

@app.post('/model/embed', response_model=EmbedResponse)
async def embed(payload: EmbedPayload):
    if _model is None:
        raise HTTPException(503, 'model not loaded')
    texts = payload.texts or []
    if not texts:
        return EmbedResponse(embeddings=[], model=_model_name, dim=_dim, count=0)
    normalize = _default_normalize if payload.normalize is None else bool(payload.normalize)
    start = time.perf_counter()
    if _semaphore:
        async with _semaphore:
            vecs = await _embed(texts, normalize)
    else:
        vecs = await _embed(texts, normalize)
    elapsed = (time.perf_counter() - start) * 1000
    return EmbedResponse(embeddings=vecs, model=_model_name, dim=_dim, count=len(vecs))

@app.get('/healthz')
async def healthz():
    return {'status': 'ok', 'model': _model_name, 'dim': _dim}

@app.get('/')
async def root():
    return {'service': 'hf_embed', 'model': _model_name, 'dim': _dim}

def load_model(name: str, device: str):
    global _model, _tokenizer, _model_name, _dim
    print(f'[load] loading {name} on {device}')
    _tokenizer = AutoTokenizer.from_pretrained(name)
    _model = AutoModel.from_pretrained(name)
    _model.to(device)
    _model.eval()
    # probe dim
    with torch.inference_mode():
        v = _encode_batch(['probe'], normalize=False)
        _dim = len(v[0]) if v else 0
    _model_name = name
    print(f'[load] ready dim={_dim}')

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=os.getenv('HF_EMBED_MODEL'))
    ap.add_argument('--host', default=os.getenv('EMBED_HOST','0.0.0.0'))
    ap.add_argument('--port', type=int, default=int(os.getenv('EMBED_PORT','8090')))
    ap.add_argument('--device', default=os.getenv('EMBED_DEVICE') or ('cuda' if torch.cuda.is_available() else 'cpu'))
    ap.add_argument('--batch-size', type=int, default=int(os.getenv('EMBED_BATCH','32')))
    ap.add_argument('--concurrency', type=int, default=int(os.getenv('EMBED_CONCURRENCY','4')))
    ap.add_argument('--normalize', action='store_true', default=os.getenv('EMBED_NORMALIZE','1')=='1')
    return ap.parse_args()

def main():  # pragma: no cover
    global _semaphore, _default_normalize, _batch_size, _device
    args = parse_args()
    if not args.model:
        raise SystemExit('--model or HF_EMBED_MODEL required')
    _device = args.device
    load_model(args.model, _device)
    _batch_size = args.batch_size
    _default_normalize = args.normalize
    _semaphore = asyncio.Semaphore(args.concurrency) if args.concurrency > 0 else None
    uvicorn.run(app, host=args.host, port=args.port, log_level='info')

if __name__ == '__main__':  # pragma: no cover
    main()
