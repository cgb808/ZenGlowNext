from __future__ import annotations
import random
import os
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from ..event_logger import log_event

SwarmType = str  # 'PRIMARY' | 'EXPLORER'

@dataclass
class PartitionTelemetry:
    last_used_step: int = -1
    hits: int = 0
    explorer_hits: int = 0
    success_ema: float = 0.0
    quality_ema: float = 0.1
    avg_latency_ms: Optional[float] = None

class PartitionScheduler:
    def __init__(
        self,
        partitions: int,
        base_explorer_prob: float = 0.2,
        quality_decay: float = 0.9,
        success_decay: float = 0.85,
        predictive_hook: Optional[Callable[[int, Dict[str, float]], Dict[str, float]]] = None,
        rag_client: Optional[object] = None,
        max_age_weight: int = 500,
    ) -> None:
        self.partitions = partitions
        self.base_explorer_prob = base_explorer_prob
        self.dynamic_explorer_prob = base_explorer_prob
        self.quality_decay = quality_decay
        self.success_decay = success_decay
        self.max_age_weight = max_age_weight
        self._t = 0
        self._least_recent = deque(range(partitions))
        self._telemetry: Dict[int, PartitionTelemetry] = {i: PartitionTelemetry() for i in range(partitions)}
        self._predictive_hook = predictive_hook
        self._rag_client = rag_client
        self._snapshot_interval = int(os.getenv("SWARM_SNAPSHOT_INTERVAL", "25"))
        self._last_snapshot_prob = self.dynamic_explorer_prob
        self._last_snapshot_t = 0

    def _pick_explorer_partition(self) -> int:
        if self._least_recent:
            return self._least_recent.popleft()
        scores: List[Tuple[float, int]] = []
        for pid, telem in self._telemetry.items():
            novelty = (1.0 - telem.success_ema) * (1.0 / (1 + telem.hits))
            scores.append((novelty, pid))
        scores.sort(reverse=True)
        return scores[0][1]

    def _pick_primary_partition(self) -> int:
        weights: List[Tuple[float, int]] = []
        for pid, telem in self._telemetry.items():
            age = self._t - telem.last_used_step if telem.last_used_step >= 0 else self._t + 1
            age = min(age, self.max_age_weight)
            weight = age * (telem.quality_ema + 0.1)
            weights.append((weight, pid))
        total = sum(w for w, _ in weights) or 1.0
        r = random.random() * total
        acc = 0.0
        for w, pid in weights:
            acc += w
            if r <= acc:
                return pid
        return weights[-1][1]

    def route(self) -> Tuple[SwarmType, int]:
        explore = random.random() < self.dynamic_explorer_prob
        if explore:
            pid = self._pick_explorer_partition()
            stype: SwarmType = 'EXPLORER'
        else:
            pid = self._pick_primary_partition()
            stype = 'PRIMARY'
        telem = self._telemetry[pid]
        telem.hits += 1
        if stype == 'EXPLORER':
            telem.explorer_hits += 1
        telem.last_used_step = self._t
        try:
            self._least_recent.remove(pid)
        except ValueError:
            pass
        self._t += 1
        if self._snapshot_interval > 0 and (self._t % self._snapshot_interval == 0):
            snap = self.snapshot()
            delta_prob = round(self.dynamic_explorer_prob - self._last_snapshot_prob, 6)
            delta_t = self._t - self._last_snapshot_t
            log_event(
                event_type="swarm_scheduler_snapshot",
                dynamic_explorer_prob=self.dynamic_explorer_prob,
                delta_explorer_prob=delta_prob,
                delta_t=delta_t,
                telemetry={
                    't': snap['t'],
                    'dynamic_explorer_prob': snap['dynamic_explorer_prob'],
                    'least_recent_remaining': snap['least_recent_remaining'],
                },
            )
            self._last_snapshot_prob = self.dynamic_explorer_prob
            self._last_snapshot_t = self._t
        return stype, pid

    def feedback(self, pid: int, success: bool, latency_ms: Optional[float] = None, quality_signal: Optional[float] = None) -> None:
        telem = self._telemetry.get(pid)
        if telem is None:
            return
        instant = 1.0 if success else 0.0
        telem.success_ema = self.success_decay * telem.success_ema + (1 - self.success_decay) * instant
        if latency_ms is not None:
            if telem.avg_latency_ms is None:
                telem.avg_latency_ms = float(latency_ms)
            else:
                telem.avg_latency_ms = 0.7 * telem.avg_latency_ms + 0.3 * latency_ms
        if quality_signal is not None:
            telem.quality_ema = self.quality_decay * telem.quality_ema + (1 - self.quality_decay) * quality_signal
        if self._predictive_hook:
            features = {
                'success_ema': telem.success_ema,
                'quality_ema': telem.quality_ema,
                'avg_latency_ms': telem.avg_latency_ms or 0.0,
                'explorer_ratio': telem.explorer_hits / telem.hits if telem.hits else 0.0,
                'age_steps': self._t - telem.last_used_step,
                'dynamic_explorer_prob': self.dynamic_explorer_prob,
                'base_explorer_prob': self.base_explorer_prob,
            }
            if self._rag_client and telem.success_ema < 0.4 and not success:
                try:
                    ctx = self._rag_client.query_past_failures(pid, telem.success_ema)  # type: ignore[attr-defined]
                except Exception:
                    ctx = None
                if ctx:
                    features['historical_context'] = ctx
            try:
                adj = self._predictive_hook(pid, features) or {}
                dq = float(adj.get('quality_delta', 0.0))
                de = float(adj.get('explorer_bias_delta', 0.0))
                if dq:
                    telem.quality_ema = max(0.01, min(2.0, telem.quality_ema + dq))
                if de:
                    self.dynamic_explorer_prob = max(0.0, min(0.9, self.dynamic_explorer_prob + de))
            except Exception:
                pass
        if success and self.dynamic_explorer_prob > self.base_explorer_prob + 0.05:
            decay = min(0.02, (self.dynamic_explorer_prob - self.base_explorer_prob) * 0.25)
            self.dynamic_explorer_prob = max(self.base_explorer_prob + 0.01, self.dynamic_explorer_prob - decay)

    def snapshot(self) -> Dict[str, object]:
        return {
            't': self._t,
            'dynamic_explorer_prob': round(self.dynamic_explorer_prob, 4),
            'partitions': {
                pid: {
                    'hits': telem.hits,
                    'explorer_pct': (telem.explorer_hits / telem.hits) if telem.hits else 0.0,
                    'success_ema': round(telem.success_ema, 4),
                    'quality_ema': round(telem.quality_ema, 4),
                    'avg_latency_ms': round(telem.avg_latency_ms, 2) if telem.avg_latency_ms is not None else None,
                    'age': self._t - telem.last_used_step if telem.last_used_step >= 0 else None,
                }
                for pid, telem in self._telemetry.items()
            },
            'least_recent_remaining': len(self._least_recent),
        }


def build_default_scheduler(partitions: int, predictive_hook=None, rag_client=None) -> PartitionScheduler:
    return PartitionScheduler(partitions=partitions, predictive_hook=predictive_hook, rag_client=rag_client)
