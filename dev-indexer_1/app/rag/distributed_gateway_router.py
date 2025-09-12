"""Distributed RAG pipeline gateway (SSE) for phased results.

Provides /rag/dstream_query which performs synchronous P0, then enqueues
P1 work onto Redis Stream and listens for P1/P2 deltas tagged by session_id.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .embedder import Embedder
from .feature_assembler import Candidate, assemble_features
from .ltr import GLOBAL_LTR_MODEL
from .pipeline_messages import (
    P0ToP1Message,
    P1ResultMessage,
    P2ResultMessage,
    RAG_P1_QUEUE,
    RAG_RESULTS_STREAM,
)
from .stream_bus import publish, read_blocks

router = APIRouter(prefix="/rag", tags=["rag-distributed"])

_embedder = Embedder()


class DistStreamQueryPayload(BaseModel):
    query: str
    top_k: int | None = None


def _ann_search_stub(vec: List[float], top_k: int) -> List[Dict[str, Any]]:
    # Placeholder using deterministic dummy hits (id, distance)
    return [
        {"id": i, "text_preview": f"Doc {i} for query", "distance": 0.01 * (i + 1)}
        for i in range(top_k)
    ]


async def _event_stream(payload: DistStreamQueryPayload) -> AsyncGenerator[str, None]:
    if not payload.query.strip():
        yield 'data: {"error":"empty query"}\n\n'
        return
    session_id = secrets.token_hex(8)
    top_k = payload.top_k or int(os.getenv("RAG_TOP_K_DEFAULT", "8"))
    q_vec = _embedder.embed_batch([payload.query])[0]
    p0_hits = _ann_search_stub(q_vec, top_k)
    p0_event = {"phase": "P0", "provisional": True, "results": p0_hits, "session_id": session_id}
    yield "data: " + json.dumps(p0_event) + "\n\n"

    # Enqueue P1 work
    msg = P0ToP1Message(session_id=session_id, query=payload.query, p0_results=p0_hits, top_k=top_k)
    publish(RAG_P1_QUEUE, json.loads(msg.to_json()))

    # Listen for P1/P2 deltas for this session
    last_id = "$"  # start from new messages only
    timeout_s = float(os.getenv("RAG_DISTRIBUTED_SSE_TIMEOUT", "25"))
    end_time = asyncio.get_event_loop().time() + timeout_s
    phases_received: set[str] = set()
    while asyncio.get_event_loop().time() < end_time:
        async for _ in _yield_once():
            pass
        for entry in _drain_stream(RAG_RESULTS_STREAM, last_id):
            if entry is None:
                await asyncio.sleep(0.2)
                continue
            last_id = entry.get("id", last_id)
            data = entry.get("data") or {}
            if data.get("session_id") != session_id:
                continue
            phase = data.get("phase")
            yield "data: " + json.dumps(data) + "\n\n"
            phases_received.add(phase)
            if data.get("final"):
                return
        await asyncio.sleep(0.25)
    # Timeout exit
    yield 'data: {"phase":"timeout","session_id":"' + session_id + '"}\n\n'


async def _yield_once():  # helper to keep an async boundary in sync loop
    yield None


def _drain_stream(stream: str, last_id: str):
    # Non-blocking consume wrapper: uses blocking read with short timeout once
    gen = read_blocks(stream, last_id=last_id, block_ms=500)
    # Pull up to a limited set per invocation
    out = []
    for _ in range(4):
        try:
            nxt = next(gen)
        except StopIteration:
            break
        out.append(nxt)
    return out


@router.post("/dstream_query")
async def dstream_query(payload: DistStreamQueryPayload):
    return StreamingResponse(_event_stream(payload), media_type="text/event-stream")
