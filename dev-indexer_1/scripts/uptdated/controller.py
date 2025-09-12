from __future__ import annotations
import os
from typing import Dict, Any, Optional
from .base import Predictor
from .models.route_calibration import RouteCalibrationPredictor

class PredictiveController:
    def __init__(self):
        self.models: Dict[str, Predictor] = {}
        self.cache: Dict[str, Dict[str, Any]] = {}  # session_id -> last predictions
        self.hits = 0
        self.misses = 0
        self.register(RouteCalibrationPredictor())

    def register(self, predictor: Predictor) -> None:
        self.models[predictor.name] = predictor

    def predict(self, name: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        m = self.models.get(name)
        if not m:
            return None
        session_id = context.get('session_id')
        cache_key = None
        if session_id:
            cache_key = f"{session_id}:{name}:{hash(context.get('text','')) & 0xffff}"
            if cache_key in self.cache:
                self.hits += 1
                return self.cache[cache_key]
        self.misses += 1
        out = m.predict(context)
        if cache_key:
            self.cache[cache_key] = out
        return out

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses or 1
        return {
            'models': list(self.models.keys()),
            'cache_hits': self.hits,
            'cache_misses': self.misses,
            'cache_hit_ratio': self.hits / total,
            'entries': len(self.cache),
        }

_controller: PredictiveController | None = None

def get_predictive_controller() -> PredictiveController:
    global _controller
    if _controller is None:
        _controller = PredictiveController()
    return _controller
