"""
Embedding generation utilities for RAG pipeline.
TODO: Implement embedding model integration.
"""

import os

import requests

EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")


def get_embedding(text: str) -> list:
    """Return embedding vector for input text using EMBED_ENDPOINT."""
    r = requests.post(EMBED_ENDPOINT, json={"texts": [text]}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["embeddings"][0]
