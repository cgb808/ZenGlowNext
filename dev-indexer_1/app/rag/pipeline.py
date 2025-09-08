"""
RAG Pipeline Core Logic
- Embedding generation
- Vector search/retrieval
- Prompt composition
"""

import math
import os
from typing import Any, Dict, List, Protocol


class SupportsEmbed(Protocol):
    def embed(self, text: str) -> List[float]: ...


class SupportsVectorSearch(Protocol):
    def vector_search(
        self, embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]: ...


class SupportsLLM(Protocol):
    def generate(self, prompt: str) -> str: ...


class RAGPipeline:
    def __init__(
        self,
        db_client: SupportsVectorSearch,
        embedder: SupportsEmbed,
        llm_client: SupportsLLM,
    ):
        self.db_client = db_client
        self.embedder = embedder
        self.llm_client = llm_client
        # Dynamic scoring weights (conceptual scoring layer)
        self.w_distance = float(os.getenv("RAG_WEIGHT_DISTANCE", "0.7"))
        self.w_recency = float(os.getenv("RAG_WEIGHT_RECENCY", "0.2"))
        self.w_metadata = float(os.getenv("RAG_WEIGHT_METADATA", "0.1"))
        self.enable_ann_hint = os.getenv("RAG_USE_ANN", "true").lower() == "true"

    def _derive_score(self, item: Dict[str, Any]) -> float:
        """Compute conceptual relevance score on-the-fly.

        distance component: transformed as 1/(1+distance)
        recency component: expects metadata.timestamp (epoch seconds)
        metadata component: simple boost if certain tags present
        """
        dist = float(item.get("distance", 0.0))
        distance_score = 1.0 / (1.0 + dist)

        meta = item.get("metadata") or {}
        ts = meta.get("timestamp")
        if ts:
            # exponential decay (half-life configurable?)
            half_life = float(
                os.getenv("RAG_RECENCY_HALF_LIFE", "604800")
            )  # 7 days seconds
            age = (
                max(
                    0.0,
                    (float(os.getenv("CURRENT_TIME_OVERRIDE", "0")) or 0) - float(ts),
                )
                if os.getenv("CURRENT_TIME_OVERRIDE")
                else 0.0
            )
            # If no CURRENT_TIME_OVERRIDE provided, skip recency weighting
            recency_score = 1.0 if age == 0 else math.exp(-age / half_life)
        else:
            recency_score = 0.5

        tags = meta.get("tags", []) if isinstance(meta, dict) else []
        tag_boost_terms = {"core", "critical", "schema"}
        metadata_score = 0.0
        if tags:
            overlap = tag_boost_terms.intersection(set(tags))
            if overlap:
                metadata_score = min(1.0, len(overlap) / len(tag_boost_terms))

        total = (
            self.w_distance * distance_score
            + self.w_recency * recency_score
            + self.w_metadata * metadata_score
        )
        return total

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for input text."""
        return self.embedder.embed(text)

    def retrieve_context(
        self, embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant context from DB using vector search."""
        return self.db_client.vector_search(embedding, top_k=top_k)

    def compose_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Compose prompt for LLM using query and retrieved context."""
        context_str = (
            "\n".join([c.get("text", "") for c in context]) or "No context found."
        )
        return f"Context:\n{context_str}\n\nQuestion: {query}\nAnswer:"

    def run(self, query: str, top_k: int = 5) -> str:
        """Full RAG pipeline: embed, retrieve, compose, generate answer."""
        embedding = self.generate_embedding(query)
        context = self.retrieve_context(embedding, top_k=top_k)
        # Enrich with dynamic relevance score
        for c in context:
            c["conceptual_score"] = self._derive_score(c)
        # Optional: sort by conceptual score descending (if ANN gave approximate order already this can refine)
        context.sort(key=lambda x: x.get("conceptual_score", 0), reverse=True)
        prompt = self.compose_prompt(query, context)
        return self.llm_client.generate(prompt)
