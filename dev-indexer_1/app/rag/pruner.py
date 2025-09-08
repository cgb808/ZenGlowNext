"""Lightweight relevance pruning for retrieved chunks.

Uses a cheap model (edge/phi3) to yes/no filter chunks before prompt assembly.
Activated when env RAG_PRUNE=1 and number of chunks > threshold.
"""
from __future__ import annotations
import os
from typing import List, Dict, Any
from .llm_client import LLMClient
from app.core import cache_metrics

_enabled = os.getenv("RAG_PRUNE", "0").lower() in {"1", "true", "yes"}
_min_chunks = int(os.getenv("RAG_PRUNE_MIN", "6"))


def prune(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not _enabled or len(chunks) < _min_chunks:
        return chunks
    try:
        cache_metrics.increment("prune_invocations")
    except Exception:
        pass
    client = LLMClient()
    kept: List[Dict[str, Any]] = []
    for c in chunks:
        text = c.get("text_preview") or ""
        if not text:
            continue
        prompt = (
            f"Question: {query}\n---\nText: {text[:800]}\n---\nIs this text relevant to answering the question? Reply only yes or no."  # noqa: E501
        )
        try:
            meta = client.generate_with_metadata(prompt, prefer="edge")
            ans = (meta.get("text") or "").strip().lower()
            if ans.startswith("y"):
                kept.append(c)
        except Exception:
            kept.append(c)  # fail-open
    # Ensure at least one
    result = kept or chunks[:1]
    try:
        cache_metrics.increment("prune_removed_{}".format(len(chunks) - len(result)))
    except Exception:
        pass
    return result

__all__ = ["prune"]
