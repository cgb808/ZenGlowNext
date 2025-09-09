from __future__ import annotations

import hashlib
from typing import List

import numpy as np

_st_model = None
try:  # optional: load sentence-transformers if available
    from sentence_transformers import SentenceTransformer  # type: ignore

    try:
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _st_model = None
except Exception:
    _st_model = None


def _hash_to_vec(text: str, dim: int = 768) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # repeat digest to fill dim
    arr = np.frombuffer(h * ((dim // len(h)) + 1), dtype=np.uint8)[:dim].astype(np.float32)
    arr /= np.linalg.norm(arr) + 1e-8
    return arr.tolist()


def get_text_embedding(text: str, dim: int = 768) -> List[float]:
    if _st_model is not None:
        try:
            vec = _st_model.encode(text, normalize_embeddings=True)
            # Ensure correct dim via pad/trim
            v = np.array(vec, dtype=np.float32)
            if v.shape[0] < dim:
                v = np.pad(v, (0, dim - v.shape[0]))
            elif v.shape[0] > dim:
                v = v[:dim]
            return v.tolist()
        except Exception:
            pass
    return _hash_to_vec(text, dim=dim)
