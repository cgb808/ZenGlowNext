from __future__ import annotations

import hashlib
from typing import Iterable, List

import numpy as np


def get_timeseries_embedding(series: Iterable[float], dim: int = 768) -> List[float]:
    arr = np.array(list(series), dtype=np.float32)
    if arr.size == 0:
        return [0.0] * dim
    # Simple spectral summary + stats as baseline
    mean = float(arr.mean())
    std = float(arr.std() + 1e-8)
    # Hash of discretized series to stabilize
    quant = np.round((arr - mean) / std, 2)
    h = hashlib.sha256(quant.tobytes()).digest()
    base = np.frombuffer(h * ((dim // len(h)) + 1), dtype=np.uint8)[:dim].astype(np.float32)
    # Mix in moments
    base[:4] = np.array([mean, std, float(arr.min()), float(arr.max())], dtype=np.float32)
    base /= np.linalg.norm(base) + 1e-8
    return base.tolist()
