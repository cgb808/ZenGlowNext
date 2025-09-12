from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Schema version for features produced here
FEATURE_SCHEMA_VERSION: int = 1


@dataclass
class Candidate:
    chunk_id: int
    text: str
    distance: float  # raw vector distance
    source: str | None = None
    meta: Dict[str, Any] | None = None


def _similarity_from_distance(d: float) -> float:
    return 1.0 / (1.0 + float(d))


def assemble_features(query: str, candidates: List[Candidate]) -> Tuple[List[List[float]], List[str]]:
    """Return (feature_matrix, feature_names) for schema v1.

    Features:
    - similarity_primary: 1/(1+distance)
    - log_length: log(len(text))
    - bias: constant 1.0
    """
    feature_names = ["similarity_primary", "log_length", "bias"]
    matrix: List[List[float]] = []
    for c in candidates:
        log_len = math.log(max(1, len(c.text)))
        sim = _similarity_from_distance(c.distance)
        matrix.append([sim, log_len, 1.0])
    return matrix, feature_names


def assemble_features_legacy(
    query: str, candidates: List[Candidate]
) -> Tuple[List[List[float]], List[str]]:  # pragma: no cover (compat path)
    """Legacy draft feature layout (schema 0.1)."""
    feature_names = ["bias", "distance_inv", "text_len_log", "query_len_log"]
    q_len_log = math.log(max(1, len(query)))
    matrix: List[List[float]] = []
    for c in candidates:
        distance_inv = _similarity_from_distance(c.distance)
        text_len_log = math.log(max(1, len(c.text)))
        matrix.append([1.0, distance_inv, text_len_log, q_len_log])
    return matrix, feature_names
