"""Message schemas & constants for distributed RAG pipeline (P0->P1->P2).

Workers communicate via Redis Streams; messages are small JSON dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import json

RAG_P1_QUEUE = "rag-pipeline-p1-queue"  # P0 gateway -> P1 LTR worker
RAG_RESULTS_STREAM = "rag-results-stream"  # P1 & P2 workers -> gateway SSE forwarder


@dataclass
class P0ToP1Message:
    session_id: str
    query: str
    p0_results: List[Dict[str, Any]]  # [{id, distance, text_preview?}]
    top_k: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class P1ResultMessage:
    session_id: str
    phase: str  # "P1"
    delta: List[Dict[str, Any]]
    result_count: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class P2ResultMessage:
    session_id: str
    phase: str  # "P2"
    delta: List[Dict[str, Any]]
    result_count: int
    final: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self))
