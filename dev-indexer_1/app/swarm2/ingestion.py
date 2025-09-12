from __future__ import annotations
import os
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

BUFFER_SIZE = int(os.getenv("SWARM_FEEDBACK_BUFFER", "50"))
EXPLORER_MAX_STEP = float(os.getenv("SWARM_EXPLORER_MAX_STEP", "0.05"))

@dataclass
class FeedbackRecord:
    success: bool
    latency_ms: float

class EventIngestionStub:
    def __init__(self, buffer_size: int = BUFFER_SIZE) -> None:
        self.buffer_size = buffer_size
        self._by_partition = defaultdict(lambda: deque(maxlen=self.buffer_size))
        self._recent_failure_phase: Dict[int, bool] = {}

    def ingest_feedback(self, partition_id: int, success: bool, latency_ms: float) -> None:
        self._by_partition[partition_id].append(FeedbackRecord(success=success, latency_ms=latency_ms))

    def recent_stats(self, partition_id: int) -> Optional[Tuple[float, float, int]]:
        dq = self._by_partition.get(partition_id)
        if not dq:
            return None
        total = len(dq)
        if total == 0:
            return None
        success_ratio = sum(1 for r in dq if r.success) / total
        avg_latency = sum(r.latency_ms for r in dq) / total
        return success_ratio, avg_latency, total

    def predictive_hook(self, partition_id: int, features: Dict[str, float]) -> Dict[str, float]:
        stats = self.recent_stats(partition_id)
        if stats is None:
            recent_success_ratio = features.get('success_ema', 0.0)
            recent_avg_latency = features.get('avg_latency_ms', 0.0)
            recent_count = 0
        else:
            recent_success_ratio, recent_avg_latency, recent_count = stats

        quality_delta = 0.0
        explorer_bias_delta = 0.0
        dynamic_prob = features.get('dynamic_explorer_prob', 0.0)
        base_prob = features.get('base_explorer_prob', 0.2)

        dq_deque: Deque[FeedbackRecord] | None = self._by_partition.get(partition_id)
        consecutive_fail_streak = 0
        if dq_deque:
            for r in reversed(dq_deque):
                if r.success:
                    break
                consecutive_fail_streak += 1
        last_event_success = None if not dq_deque else dq_deque[-1].success

        raw_hist_ctx = features.get('historical_context')
        hist_ctx: Optional[str] = raw_hist_ctx if isinstance(raw_hist_ctx, str) else None
        if hist_ctx is not None:
            lowered = hist_ctx.lower()
            if 'typically recovered' in lowered or 'transient' in lowered:
                if dynamic_prob < base_prob + 0.05 and recent_success_ratio < 0.6:
                    explorer_bias_delta += min(EXPLORER_MAX_STEP, 0.01)
                    quality_delta += 0.005
            if 'persistent failure' in lowered or 'extended degradation' in lowered:
                if dynamic_prob < 0.85:
                    explorer_bias_delta += min(EXPLORER_MAX_STEP, 0.04)
                quality_delta -= 0.02

        if (
            recent_count >= 2
            and recent_success_ratio < 0.35
            and consecutive_fail_streak >= 1
            and last_event_success is False
            and dynamic_prob <= base_prob + 0.08
        ):
            explorer_bias_delta += min(EXPLORER_MAX_STEP, 0.02 + (0.005 if recent_avg_latency > 150 else 0.0))
            quality_delta += 0.01
        elif recent_success_ratio > 0.8 and recent_avg_latency < 120 and recent_count >= 5:
            trim = 0.01
            if dynamic_prob > base_prob * 0.5:
                explorer_bias_delta -= min(EXPLORER_MAX_STEP, trim)
            quality_delta += (recent_success_ratio - 0.8) * 0.012
        else:
            quality_delta += (recent_success_ratio - features.get('quality_ema', 0.0)) * 0.01
            if last_event_success:
                if dynamic_prob > base_prob + 0.05:
                    explorer_bias_delta -= min(EXPLORER_MAX_STEP, 0.015)

        return {
            'quality_delta': max(-0.05, min(0.05, quality_delta)),
            'explorer_bias_delta': max(-EXPLORER_MAX_STEP, min(EXPLORER_MAX_STEP, explorer_bias_delta)),
        }

_INGESTION = EventIngestionStub()

def get_ingestion() -> EventIngestionStub:
    return _INGESTION
