"""Central Control utilities for assembling dynamic tutor prompts and summaries.

Pure helpers only; no network or DB side effects here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional


@dataclass
class UserProfile:
    name: str
    goals: Optional[str] = None
    learning_style: Optional[str] = None


@dataclass
class SessionState:
    last_interaction_minutes: Optional[int] = None
    last_agent: Optional[str] = None
    last_topic_summary: Optional[str] = None
    last_ai_response: Optional[str] = None


def _fmt_minutes(mins: Optional[int]) -> str:
    try:
        if mins is None:
            return "unknown"
        return f"{int(mins)} minutes"
    except Exception:
        return "unknown"


def build_cheat_sheet(
    user: UserProfile,
    session: SessionState,
    insights: Iterable[str] | None = None,
    system_instructions: str = "YOU ARE A HELPFUL AI TUTOR",
) -> str:
    """Assemble the invisible preamble (cheat sheet) block.

    Returns a string block matching the provided example structure.
    """
    insights_list = list(insights or [])
    lines: list[str] = []
    lines.append(f"--- SYSTEM INSTRUCTIONS: {system_instructions} ---")
    lines.append("\n--- USER CHEAT SHEET (BRIEFING DOCUMENT) ---")
    lines.append(f"  - User: {user.name}")
    if user.goals:
        lines.append(f"  - Known Goals: {user.goals}")
    if user.learning_style:
        lines.append(f"  - Learning Style: {user.learning_style}")
    lines.append("\n--- SESSION STATE (CONTINUING CONVERSATION) ---")
    lines.append(f"  - Time Since Last Interaction: {_fmt_minutes(session.last_interaction_minutes)}")
    if session.last_topic_summary:
        lines.append(f"  - Last Topic: {session.last_topic_summary}")
    if session.last_ai_response:
        lines.append(f"  - Your Last Response: \"{session.last_ai_response}\"")
    lines.append("\n--- RELEVANT KNOWLEDGE (From RAG) ---")
    if insights_list:
        for s in insights_list:
            lines.append(f"  - Insight: {s}")
    else:
        lines.append("  - Insight: (none)")
    lines.append("--- END OF CHEAT SHEET ---")
    return "\n".join(lines)


def build_tutor_prompt(
    user_prompt: str,
    user: UserProfile,
    session: SessionState,
    insights: Iterable[str] | None = None,
    system_instructions: str = "YOU ARE A HELPFUL AI TUTOR",
) -> str:
    """Construct the final prompt sent to the LLM.

    This includes the cheat sheet preamble followed by the user's new prompt.
    """
    preamble = build_cheat_sheet(
        user=user,
        session=session,
        insights=insights,
        system_instructions=system_instructions,
    )
    guidance: list[str] = []
    if (user.learning_style or "").lower().strip().startswith("prefers step-by-step"):
        guidance.append("Please provide step-by-step examples where helpful.")
    guidance_str = ("\n" + " ".join(guidance)) if guidance else ""
    return f"{preamble}\n\n[USER'S NEW PROMPT]{guidance_str}\n{user_prompt}".strip()


def build_session_summary_prompt(transcript: list[dict[str, Any]] | None) -> str:
    """Create a concise summarization instruction for the session transcript.

    transcript is a list of {role: 'user'|'assistant', content: str}.
    """
    return (
        "Summarize the session in 1-2 sentences, focusing on topic progression and next steps.\n"
        "Keep it concise and student-friendly."
    )
