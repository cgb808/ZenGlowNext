"""Feature Assembly Scaffold (Artifact B)

Produces deterministic feature vectors for candidate chunks.
Future expansion points (not yet implemented):
  * recency / freshness
  * engagement aggregates (chunk_engagement_stats)
  * content & authority scores (chunks table)
  * personalization signals

Current minimal features (schema v1):
  0 similarity_primary (1/(1+distance))
  1 log_length (natural log of text length)
  2 bias (constant 1.0)

Backwards compatibility: earlier draft (schema 0.1) used [bias, distance_inv, text_len_log, query_len_log].
We preserve a compatibility function to map previous ordering when needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

FEATURE_SCHEMA_VERSION = 1  # integer for easier comparison


@dataclass
class Candidate:
    chunk_id: int
    text: str
    distance: float  # raw vector distance
    source: str | None = None
    meta: Dict[str, Any] | None = None


def _similarity_from_distance(d: float) -> float:
    return 1.0 / (1.0 + d)


def assemble_features(
    query: str, candidates: List[Candidate]
) -> Tuple[List[List[float]], List[str]]:
    """Return (feature_matrix, feature_names) for schema v1."""
    feature_names = ["similarity_primary", "log_length", "bias"]
    matrix: List[List[float]] = []
    for c in candidates:
        length = len(c.text)
        log_len = math.log(max(length, 1))
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
        distance_inv = 1.0 / (1.0 + c.distance)
        text_len_log = math.log(max(1, len(c.text)))
        matrix.append([1.0, distance_inv, text_len_log, q_len_log])
    return matrix, feature_names
