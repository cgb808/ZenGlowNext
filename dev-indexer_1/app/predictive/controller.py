"""Predictive Controller implementation.

Lightweight host for embedded micro-models. Currently supports
`route_calibration` model. Designed for near-zero overhead when
disabled (caller should guard construction behind env flags).

API surface expected by `switchr_router`:
  - get_predictive_controller() -> PredictiveController (singleton)
  - .predict(model_name: str, context: dict) -> dict | None
  - .stats() -> dict (cache + registered models)

Design notes:
  - In-process only; no external network calls.
  - Simple feature hash cache keyed by model + sorted feature pairs.
  - Each model module exposes a class with a `predict(context)` method OR
    a top-level function `predict(context)` returning a mapping.
"""
from __future__ import annotations

from typing import Any, Dict, Callable
import hashlib
import threading

from .models import route_calibration as route_calibration_mod
from app.core import metrics_facade as _metrics


class PredictiveController:
    def __init__(self) -> None:
        self._models: dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._cache: dict[str, Dict[str, Any]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._lock = threading.Lock()
        self._load_models()

    # ---------------- Model Loading -----------------
    def _load_models(self) -> None:  # extend here for more models
        # route_calibration
        if hasattr(route_calibration_mod, "RouteCalibrationPredictor"):
            inst = route_calibration_mod.RouteCalibrationPredictor()
            self._models[inst.name] = inst.predict  # type: ignore[assignment]
        elif hasattr(route_calibration_mod, "predict"):
            self._models["route_calibration"] = getattr(route_calibration_mod, "predict")

    # ---------------- Public API --------------------
    def predict(self, model: str, context: Dict[str, Any]) -> Dict[str, Any] | None:
        fn = self._models.get(model)
        if not fn:
            return None
        # Build cache key from model + deterministic feature extraction snapshot
        # (Shallow: we rely on model's own feature extraction determinism.)
        try:
            # Represent context minimally to stabilize hashing (only str/int/float/bool)
            items = []
            for k in sorted(context.keys()):
                v = context[k]
                if isinstance(v, (str, int, float, bool)) or v is None:
                    items.append(f"{k}={v}")
            key_raw = model + "|" + "&".join(items)
            key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()
        except Exception:
            key = None  # fallback: no caching

        if key is not None:
            with self._lock:
                if key in self._cache:
                    self._cache_hits += 1
                    # metrics: hit
                    _metrics.counter("predictive_cache_hits", inc=1, model=model)
                    return self._cache[key]

        out: Dict[str, Any]
        try:
            out = fn(context)  # type: ignore[misc]
            if not isinstance(out, dict):  # normalize
                out = {"result": out}
        except Exception as e:  # noqa: BLE001
            # Fail closed: return None so caller just skips adjustment
            out = {"error": f"model_error:{e.__class__.__name__}"}

        if key is not None:
            with self._lock:
                # New entry (miss)
                self._cache[key] = out
                self._cache_misses += 1
                _metrics.counter("predictive_cache_misses", inc=1, model=model)
                # Track current cache size as observation (light gauge proxy)
                _metrics.observe("predictive_cache_size", float(len(self._cache)), model=model)
        return out

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            size = len(self._cache)
            hits = self._cache_hits
            misses = self._cache_misses
        ratio = hits / (hits + misses) if (hits + misses) else 0.0
        return {
            "models": sorted(self._models.keys()),
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_ratio": ratio,
            "cache_entries": size,
        }

    # -------- Testing / Maintenance Utilities ---------
    def reset_cache(self) -> None:
        """Clear predictive cache & associated counters (test helper)."""
        with self._lock:
            self._cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0


_singleton: PredictiveController | None = None
_singleton_lock = threading.Lock()


def get_predictive_controller() -> PredictiveController:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:  # double-checked
                _singleton = PredictiveController()
    return _singleton


def reset_predictive_cache() -> None:
    """Module-level helper for tests to reset controller cache if instantiated."""
    global _singleton
    if _singleton is not None:
        _singleton.reset_cache()
