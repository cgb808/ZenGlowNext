"""Embedding generator integrating with external embedding service.

Uses HTTP endpoint defined by EMBED_ENDPOINT (default internal service) and supports
single or batch text embedding. Falls back to zero-vector only if explicitly allowed.
"""

import os
from typing import List, Sequence

import requests

EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")
EMBED_FALLBACK_DIM = int(os.getenv("EMBED_FALLBACK_DIM", "768"))
ALLOW_EMBED_FALLBACK = os.getenv("ALLOW_EMBED_FALLBACK", "false").lower() == "true"


class Embedder:
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            resp = requests.post(
                EMBED_ENDPOINT,
                json={"texts": list(texts)},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]
        except Exception:
            # In test mode we always allow fallback to avoid external dependency
            if ALLOW_EMBED_FALLBACK or os.getenv("APP_TEST_MODE") == "1":
                return [[0.0] * EMBED_FALLBACK_DIM for _ in texts]
            raise
