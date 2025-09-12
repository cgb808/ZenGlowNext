"""Voice Fragment Router

Endpoint: POST /switchr/voice/fragment
Purpose: Accept streaming STT fragments for a session, accumulate text, and (optionally)
         return a routing decision using existing /switchr/route heuristics.

MVP Behavior:
  - Always returns current accumulated text length and last route decision.
  - Triggers a fresh routing decision when:
        * is_final == True OR
        * accumulated length delta >= MIN_ROUTE_DELTA tokens since last decision

Future Enhancements:
  - Adaptive timing (debounce), silence detection, intent classifier integration,
    clarification band, streaming partial persona generation.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.central_control.session_state import append_fragment, get_session
from app.central_control.switchr_router import route as core_route, RouteRequest

router = APIRouter(prefix="/switchr/voice", tags=["switchr-voice"])

MIN_ROUTE_DELTA = 8  # tokens difference threshold for re-route when not final


class VoiceFragment(BaseModel):
    session_id: str = Field(..., description="Client session identifier")
    fragment: str = Field("", description="Transcribed text fragment (may be partial)")
    is_final: bool = Field(False, description="Marks end of an utterance/turn")
    trigger_route: bool = Field(True, description="Force a routing attempt even if delta small")


class VoiceRouteResponse(BaseModel):
    session_id: str
    accum_text: str
    chars: int
    turns: int
    routed: bool
    route_backend: Optional[str] = None
    route_confidence: Optional[float] = None
    route_reasons: Optional[list[str]] = None
    latency_ms: Optional[float] = None
    is_final: bool
    delta_tokens: int


def _token_count(text: str) -> int:
    # Simple whitespace tokenization; future replace with approximate model tokenization
    return len(text.split())


@router.post("/fragment", response_model=VoiceRouteResponse)
async def ingest_fragment(payload: VoiceFragment) -> VoiceRouteResponse:
    snap_before = get_session(payload.session_id)
    before_tokens = _token_count(snap_before['accum_text'])
    updated = append_fragment(payload.session_id, payload.fragment, payload.is_final)
    after_tokens = _token_count(updated['accum_text'])
    delta_tokens = after_tokens - before_tokens

    should_route = payload.is_final or payload.trigger_route and delta_tokens >= MIN_ROUTE_DELTA
    decision = None
    start = time.time()
    if should_route and updated['accum_text']:
        # Reuse existing switchr route logic (heuristics + fallback) without tool classification
        req = RouteRequest(
            text=updated['accum_text'],
            allow_tools=False,
            classify_tools=False,
            prefer=None,
            require_reasoning=False,
        )
        decision = await core_route(req)  # type: ignore[arg-type]
    latency_ms = (time.time() - start) * 1000 if decision else None

    return VoiceRouteResponse(
        session_id=payload.session_id,
        accum_text=updated['accum_text'],
        chars=len(updated['accum_text']),
        turns=updated['turns'],
        routed=decision is not None,
        route_backend=getattr(decision, 'backend', None),
        route_confidence=getattr(decision, 'confidence', None),
        route_reasons=getattr(decision, 'reasons', None),
        latency_ms=latency_ms,
        is_final=updated['is_final'],
        delta_tokens=delta_tokens,
    )

__all__ = ["router"]
