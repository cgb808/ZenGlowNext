from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from app.embeddings.text_embedder import get_text_embedding
from app.embeddings.timeseries_embedder import get_timeseries_embedding


WEIGHTS: Dict[str, float] = {
    "content": 0.6,
    "context": 0.3,
    "intent": 0.1,
}


def _norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n > 0:
        return v / n
    return v


def get_composite_contextual_embedding(event: Dict[str, Any]) -> List[float]:
    dim = 768
    # Layer 1: content (multi-modal switch by event_type)
    content = np.zeros(dim, dtype=np.float32)
    et = event.get("event_type") or event.get("eventType")
    payload = event.get("payload") or event.get("dataPayload") or {}
    if et == "conversation_segment" and "text" in payload:
        content = np.array(get_text_embedding(str(payload.get("text")), dim=dim), dtype=np.float32)
    elif et == "heart_rate_spike" and "series_data" in payload:
        series = payload.get("series_data") or []
        try:
            series_list = list(map(float, series))  # type: ignore[arg-type]
        except Exception:
            series_list = []
        content = np.array(get_timeseries_embedding(series_list), dtype=np.float32)
    # TODO: add audio/image encoders as available (e.g., CLIP)

    # Layer 2: context
    md = event.get("metadata", {})
    context_str = (
        f"User: {md.get('user_id') or md.get('userID')}, "
        f"Location: {md.get('location')}, "
        f"Time: {md.get('timestamp') or event.get('timestamp')}"
    )
    context = np.array(get_text_embedding(context_str, dim=dim), dtype=np.float32)

    # Layer 3: intent
    intent = event.get("intent", {})
    intent_str = f"Goal: {intent.get('active_mission') or intent.get('goal')}"
    intent_v = np.array(get_text_embedding(intent_str, dim=dim), dtype=np.float32)

    # Combine
    fused = (
        WEIGHTS["content"] * content
        + WEIGHTS["context"] * context
        + WEIGHTS["intent"] * intent_v
    )
    fused = _norm(fused)
    return fused.astype("float32").tolist()
