"""Predefined assistant persona styles for prompt conditioning.

Keep instructions concise to minimize token overhead. These can be extended
later or overridden via the ASSISTANT_PERSONA environment variable (which takes
precedence when no persona_key provided by the client).
"""

from __future__ import annotations

PERSONAS: dict[str, str] = {
    "british_butler": (
        "You are a composed British butler-style AI: precise, efficient, lightly witty, never verbose."
    ),
    "neutral": (
        "You are a neutral, professional assistant. Provide clear, direct answers without unnecessary fluff."
    ),
    "fun_supportive": (
        "You are upbeat and encouraging. Stay concise while keeping a friendly, motivating tone."
    ),
    "terse_expert": (
        "You are a terse expert consultant. Deliver only essential facts and actionable guidance."
    ),
}

DEFAULT_PERSONA_KEY = "british_butler"


def resolve_persona(key: str | None, env_override: str | None) -> str:
    """Return the final persona instruction string.

    Priority order:
        1. If key matches a predefined persona -> that persona.
        2. Else if env_override (ASSISTANT_PERSONA) provided -> env_override.
        3. Fallback to DEFAULT_PERSONA_KEY.
    """
    if key and key in PERSONAS:
        return PERSONAS[key]
    if env_override:
        return env_override
    return PERSONAS[DEFAULT_PERSONA_KEY]
"""Persona resolution stub.

Defines DEFAULT_PERSONA_KEY, PERSONAS dict, and resolve_persona() expected by
`app.main`. Real persona enrichment logic can replace this later.
"""

from __future__ import annotations

from typing import Dict

DEFAULT_PERSONA_KEY = "default"
PERSONAS: Dict[str, str] = {
    DEFAULT_PERSONA_KEY: (
        "You are a helpful assistant. Answer clearly and concisely with helpful detail where relevant."
    )
}


def resolve_persona(key: str | None, env_override: str | None = None) -> str:
    if env_override:
        return env_override
    if key and key in PERSONAS:
        return PERSONAS[key]
    return PERSONAS[DEFAULT_PERSONA_KEY]
