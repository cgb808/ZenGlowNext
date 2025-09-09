"""Switchr Router

Lightweight heuristic + (optional) tiny tool controller assisted router for
sub-150ms backend selection and tool plan hints.

Endpoint(s):
  POST /switchr/route  -> Decide LLM backend and (optional) tool classification
  GET  /switchr/health -> Basic readiness + feature availability

Design Goals:
  - Fast: avoid heavy model inference unless explicitly requested
  - Transparent: return reasons & feature flags
  - Extensible: pluggable strategy phases (heuristics -> tiny -> leonardo)

Future Extensions:
  - Confidence calibration using historical success metrics
  - Feedback loop: client can POST outcome quality to /switchr/feedback
"""

from __future__ import annotations

import importlib
import logging
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

log = logging.getLogger("app.switchr")
router = APIRouter(prefix="/switchr", tags=["switchr-router"])


# ---------------------------- Models ---------------------------------
class RouteRequest(BaseModel):
    text: str = Field(..., description="User query / utterance")
    allow_tools: bool = Field(True, description="Whether tool use is permitted")
    prefer: Optional[str] = Field(None, description="Hard override backend preference")
    require_reasoning: bool = Field(
        False, description="Force deeper reasoning model (Leonardo)"
    )
    classify_tools: bool = Field(
        False, description="Attempt tiny tool classification if available"
    )


class ToolClassification(BaseModel):
    domain: str
    tools: List[str]
    confidence: float
    raw: Dict[str, Any] = {}


class RouteDecision(BaseModel):
    backend: str
    confidence: float
    reasons: List[str]
    latency_ms: float
    tool_classification: Optional[ToolClassification] = None
    features: Dict[str, bool]


# ----------------------- Tiny Controller Loader ----------------------
_tiny_loaded = False
_TinyToolController = None
_tiny_instance = None


def _load_tiny_controller():
    global _tiny_loaded, _TinyToolController, _tiny_instance
    if _tiny_loaded:
        return _tiny_instance
    _tiny_loaded = True
    try:
        mod = importlib.import_module("app.audio.integrated_audio_pipeline")
        _TinyToolController = getattr(mod, "TinyToolController", None)
        if _TinyToolController:
            _tiny_instance = _TinyToolController()
            log.info("switchr.tiny_controller.loaded")
    except Exception as e:  # noqa: BLE001
        log.warning("switchr.tiny_controller.unavailable %s", e)
    return _tiny_instance


CODE_PATTERNS = re.compile(
    r"\b(def |class |import |function|SELECT |INSERT |UPDATE |{ |};)", re.IGNORECASE
)
MATH_PATTERNS = re.compile(
    r"\b(integral|derivative|theorem|matrix|algebra|proof|equation)\b", re.IGNORECASE
)
SCIENCE_PATTERNS = re.compile(
    r"\b(cell|protein|quantum|neuron|biology|physics)\b", re.IGNORECASE
)


def _heuristic_backend(
    text: str, require_reasoning: bool
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    lower = text.lower()
    length = len(text.split())
    # Base scores
    score_leonardo = 0.0
    score_jarvis = 0.0  # phi3 specialists bucket
    score_edge = 0.0

    if require_reasoning:
        score_leonardo += 2.5
        reasons.append("require_reasoning flag")

    if length > 60:
        score_leonardo += 1.5
        reasons.append("long_query")
    elif length < 12:
        score_edge += 0.5
        reasons.append("short_query")

    if CODE_PATTERNS.search(text):
        score_jarvis += 1.4
        reasons.append("code_pattern_match")
    if MATH_PATTERNS.search(text):
        score_jarvis += 0.8
        reasons.append("math_pattern_match")
    if SCIENCE_PATTERNS.search(text):
        score_jarvis += 0.6
        reasons.append("science_pattern_match")

    if any(k in lower for k in ("explain", "analyze", "compare", "reason")):
        score_leonardo += 1.0
        reasons.append("analysis_keywords")

    # Light preference for edge if trivial Q
    if length < 8 and "?" in text:
        score_edge += 0.8
        reasons.append("trivial_question")

    scored = [
        ("leonardo", score_leonardo),
        ("jarvis", score_jarvis),
        ("edge", score_edge),
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    best, best_score = scored[0]
    total = sum(s for _, s in scored) or 1.0
    confidence = min(0.95, max(0.15, best_score / total))
    return best, confidence, reasons


@router.post("/route", response_model=RouteDecision)
async def route(req: RouteRequest) -> RouteDecision:
    start = time.time()
    # Hard override
    reasons: list[str] = []
    if req.prefer:
        reasons.append(f"hard_preference:{req.prefer}")
        backend = req.prefer
        confidence = 0.99
    else:
        backend, confidence, heur_reasons = _heuristic_backend(
            req.text, req.require_reasoning
        )
        reasons.extend(heur_reasons)

    tool_cls: ToolClassification | None = None
    if req.classify_tools and req.allow_tools:
        controller = _load_tiny_controller()
        if controller is not None:
            try:
                # Method name variability: classify or classify_tools
                if hasattr(controller, "classify_tools"):
                    raw = await controller.classify_tools(req.text)  # type: ignore[attr-defined]
                elif hasattr(controller, "classify"):
                    raw = await controller.classify(req.text)  # type: ignore[attr-defined]
                else:
                    raw = {"domain": "unknown", "tools": []}
                domain = (
                    raw.get("domain", "unknown") if isinstance(raw, dict) else "unknown"
                )
                tools = raw.get("tools", []) if isinstance(raw, dict) else []
                tool_cls = ToolClassification(
                    domain=domain,
                    tools=tools,
                    confidence=(
                        float(raw.get("confidence", 0.6))
                        if isinstance(raw, dict)
                        else 0.5
                    ),
                    raw=raw if isinstance(raw, dict) else {"raw": str(raw)},
                )
                reasons.append(f"tool_domain:{domain}")
            except Exception as e:  # noqa: BLE001
                log.warning("switchr.tool_classification_failed %s", e)
        else:
            reasons.append("tiny_controller_unavailable")

    latency_ms = (time.time() - start) * 1000
    return RouteDecision(
        backend=backend,
        confidence=confidence,
        reasons=reasons,
        latency_ms=latency_ms,
        tool_classification=tool_cls,
        features={
            "tiny_controller": _tiny_instance is not None,
            "tool_classification": tool_cls is not None,
        },
    )


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "tiny_controller": _tiny_instance is not None,
        "version": 1,
    }
