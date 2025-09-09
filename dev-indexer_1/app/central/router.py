"""Central Control router: assembles a dynamic cheat sheet prompt and orchestrates replies.

Endpoints:
- GET /central/ping: health check
- POST /central/assemble: build the cheat sheet block from provided context
- POST /central/reply: assemble + call LLM (prefers mistral) and return reply with metadata
- POST /central/session/update: summarize and persist session state (best-effort; no-op if DB unavailable)

Design notes:
- Keeps dependencies optional. If LLMClient/DBClient aren't available, uses safe stubs.
- Returns simple dicts in responses, matching project conventions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
    from app.rag.llm_client import LLMClient  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    class LLMClient:  # type: ignore
        def generate_with_metadata(self, prompt: str, prefer: str = "auto") -> Dict[str, Any]:
            # Minimal echo fallback
            return {"text": "(stub answer)", "backend": "stub", "total_latency_ms": 0.0}

try:
    from app.rag.db_client import DBClient  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    class DBClient:  # type: ignore
        def __init__(self, dsn: Optional[str] = None) -> None:
            self.dsn = dsn

        def execute(self, *_a, **_kw):
            return None

        def close(self) -> None:
            return None

from .control import (
    UserProfile,
    SessionState,
    build_cheat_sheet,
    build_tutor_prompt,
    build_session_summary_prompt,
)


router = APIRouter(prefix="/central", tags=["central"])


# ---------- Models (API IO) ----------


class ProfileIn(BaseModel):
    user_name: str = Field(..., description="Display name of the user")
    known_goals: Optional[str] = Field(None, description="Known goals summary")
    learning_style: Optional[str] = Field(None, description="Learning style preference")


class SessionIn(BaseModel):
    last_interaction_minutes: Optional[int] = Field(None)
    last_agent: Optional[str] = Field(None)
    last_topic_summary: Optional[str] = Field(None)
    last_ai_response: Optional[str] = Field(None)


class AssembleIn(BaseModel):
    profile: ProfileIn
    session: SessionIn
    insights: List[str] = Field(default_factory=list)
    system_instructions: str = Field("YOU ARE A HELPFUL AI TUTOR")


class AssembleOut(BaseModel):
    cheat_sheet: str


class ReplyIn(AssembleIn):
    user_prompt: str
    prefer: str = Field("jarvis", description="LLM backend preference (default jarvis)")


class ReplyOut(BaseModel):
    text: str
    prompt: str
    meta: Dict[str, Any]
    cheat_sheet: str


class SessionUpdateIn(BaseModel):
    user_id: str
    transcript: List[Dict[str, Any]] = Field(default_factory=list, description="[{role, content}] chronological")
    last_ai_response: Optional[str] = None
    dry_run: bool = False


class SessionUpdateOut(BaseModel):
    ok: bool
    summary: str
    dry_run: bool


# ---------- Routes ----------


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    return {"ok": True, "service": "central"}


@router.post("/assemble", response_model=AssembleOut)
async def assemble(payload: AssembleIn) -> AssembleOut:
    profile = UserProfile(
        name=payload.profile.user_name,
        goals=payload.profile.known_goals,
        learning_style=payload.profile.learning_style,
    )
    session = SessionState(
        last_interaction_minutes=payload.session.last_interaction_minutes,
        last_agent=payload.session.last_agent,
        last_topic_summary=payload.session.last_topic_summary,
        last_ai_response=payload.session.last_ai_response,
    )
    cheat = build_cheat_sheet(
        user=profile,
        session=session,
        insights=payload.insights,
        system_instructions=payload.system_instructions,
    )
    return AssembleOut(cheat_sheet=cheat)


@router.post("/reply", response_model=ReplyOut)
async def reply(payload: ReplyIn) -> ReplyOut:
    profile = UserProfile(
        name=payload.profile.user_name,
        goals=payload.profile.known_goals,
        learning_style=payload.profile.learning_style,
    )
    session = SessionState(
        last_interaction_minutes=payload.session.last_interaction_minutes,
        last_agent=payload.session.last_agent,
        last_topic_summary=payload.session.last_topic_summary,
        last_ai_response=payload.session.last_ai_response,
    )
    cheat = build_cheat_sheet(
        user=profile,
        session=session,
        insights=payload.insights,
        system_instructions=payload.system_instructions,
    )
    prompt = build_tutor_prompt(
        user_prompt=payload.user_prompt,
        user=profile,
        session=session,
        insights=payload.insights,
        system_instructions=payload.system_instructions,
    )
    llm = LLMClient()
    meta = llm.generate_with_metadata(prompt, prefer=payload.prefer)
    text = str(meta.get("text", ""))
    return ReplyOut(text=text, prompt=prompt, meta=meta, cheat_sheet=cheat)


@router.post("/session/update", response_model=SessionUpdateOut)
async def session_update(payload: SessionUpdateIn) -> SessionUpdateOut:
    summary_prompt = build_session_summary_prompt(payload.transcript)
    llm = LLMClient()
    gen = llm.generate_with_metadata(summary_prompt, prefer="jarvis")
    summary = str(gen.get("text", ""))

    if payload.dry_run:
        return SessionUpdateOut(ok=True, summary=summary, dry_run=True)

    # Persist best-effort; tolerate missing DB setup
    try:
        db = DBClient()
        db.execute(
            """
            insert into user_session_state(user_id, last_summary, last_ai_response, updated_at)
            values (%(user_id)s, %(summary)s, %(last_ai)s, now())
            on conflict (user_id)
            do update set last_summary = excluded.last_summary,
                          last_ai_response = excluded.last_ai_response,
                          updated_at = now();
            """,
            {"user_id": payload.user_id, "summary": summary, "last_ai": payload.last_ai_response},
        )
        db.close()
    except Exception:
        pass

    return SessionUpdateOut(ok=True, summary=summary, dry_run=False)


__all__ = ["router"]
