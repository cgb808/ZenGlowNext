# Predictive Controller

The predictive controller provides a lightweight, pluggable host for *embedded micro‑models* that refine routing and other real‑time decisions without introducing heavy infrastructure. It is intentionally simple: in‑process execution, no external network calls, and an optional per‑session (hash key) cache.

## Goals
- Centralize tiny predictive heuristics / models behind a uniform interface.
- Keep models cheap (< 200µs typical) and side‑effect free.
- Allow *opt‑in* activation via environment flags so default runtime cost is ~zero.
- Provide structured stats (cache hits/misses, model usage) surfaced through `/switchr/health`.

## Current Scope
Model: `route_calibration` (logistic style score with a bounded confidence adjustment)
Purpose: Nudge the router confidence slightly (|Δ| <= ~0.05) based on:
- Text length bucket
- Recent fallback rate
- Basic keyword weighting (see `models/route_calibration.py`)

Adjustment is appended to the routing reasons list as: `route_calib_adj:+0.030` (signed, 3 decimals) plus a `route_calib_applied` tag.

## Activation
Set `ENABLE_ROUTE_CALIB=1` in the environment before process start.
If disabled (default), zero overhead except a boolean check.

## Router Integration
In `switchr_router.route`:
1. Core heuristic picks backend & base confidence.
2. Low-confidence fallback to `jarvis` still happens first.
3. Predictive calibration (if enabled) receives context:
   - `text`
   - `recent_fallback_rate` (rolling ratio from `_route_stats`)
   - `session_id` (reserved placeholder for future session plumbing)
4. Returned `adjustment` (if any) is applied and clamped to [0.0, 0.99].

## Health Metrics (`/switchr/health`)
Adds:
```json
{
  "predictive_enabled": true,
  "fallback_rate": 0.12,
  "predictive_cache": {
    "models": ["route_calibration"],
    "cache_hits": 14,
    "cache_misses": 37,
    "cache_hit_ratio": 0.2745
  }
}
```
If an error occurs retrieving stats, `predictive_cache` will contain `{ "error": "predictive_stats_failed" }`.

## Cache Semantics
- Simple in‑memory dict keyed by model+hash of a frozen feature mapping.
- Eviction: none (tiny footprint). Future: optional LRU if growth becomes material.

## Extension Pattern
To add a new model:
1. Create `app/predictive/models/<name>.py` exposing a `predict(context: dict) -> dict`.
2. Register it in `PredictiveController._load_models`.
3. Gate activation behind its own `ENABLE_<NAME>` or reuse a composite flag.
4. Add any new feature extraction helpers to `features.py`.
5. Surface relevant summary stats via `stats()` (avoid raw text to protect privacy & reduce payload size).

## Design Constraints
- No outbound network I/O.
- Keep per-call latency extremely small; prefer arithmetic over importing heavy ML libs.
- Adjustments must be *advisory*, not hard overrides (router heuristics retain primacy).
- All changes observable via reasons list for auditability.

## Future Roadmap (Planned)
- Anomaly detector: flag unusually rapid fallback oscillations.
- Vector parameter selector: choose embedding variant / search params.
- Cache hit forecast: pre-warm or adjust retrieval strategy.
- Predictive signals store: persisted, aggregated feature rollups (daily histogram of outcomes).
- Session plumbing: pass stable session ids to enable short-lived temporal features.

## Safety & Observability
- Transparent: every applied adjustment emits a reason code.
- Bounded: confidence clamped to avoid artificial certainty.
- Opt-out: default flag keeps system behavior identical to pre-integration.

---
Last updated: initial integration.
