from __future__ import annotations
from typing import Optional, List
import random

class HistoricalRagClient:
    def __init__(self, connection_details: Optional[str] = None):
        self._connection_details = connection_details or "in-memory"
        self._samples: List[str] = [
            "Similar past failures on partition {pid} were due to data source lag and typically recovered within 30 steps.",
            "Historical pattern: transient spike in latency led to short term drop; system self-corrected without intervention.",
            "Persistent failure previously required model refresh and aggressive exploration for ~50 steps.",
            "Past incidents: configuration mismatch caused extended degradation until manual fix (persistent failure).",
        ]

    def query_past_failures(self, partition_id: int, current_success: float) -> Optional[str]:
        if current_success > 0.55:
            return None
        if current_success > 0.25:
            template = self._samples[0]
        else:
            template = random.choice(self._samples[2:]) if random.random() < 0.4 else self._samples[0]
        return template.format(pid=partition_id)

__all__ = ["HistoricalRagClient"]
