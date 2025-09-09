"""Core configuration helpers and lightweight /config endpoints.

Only implements what `app.main` expects:
  - apply_backward_compat_env(): mutate env for older var names (noop for now).
  - validate_required_env(): return list of missing required vars (kept small so
        service can still boot in dev / test).
  - config_router: FastAPI router exposing minimal diagnostic endpoints.

Design goals:
  - Avoid raising at import time; return missing list so caller can surface.
  - Keep required set intentionally tiny.
"""

from __future__ import annotations

import os
from typing import Dict

from fastapi import APIRouter

_REQUIRED_VARS = [
    # Intentionally minimal; DB password comes from secret file so not required here.
    # Add more when genuinely mandatory for startup logic.
    "PG_EMBED_DIM",
]


def apply_backward_compat_env() -> bool:
    """Apply backward compatibility shims; return True if any mutation occurred."""
    mutated = False
    # Example (disabled):
    # if 'OLD_DB_DSN' in os.environ and 'DATABASE_URL' not in os.environ:
    #     os.environ['DATABASE_URL'] = os.environ['OLD_DB_DSN']
    #     mutated = True
    return mutated


def validate_required_env() -> list[str]:
    """Return list of required env vars that are missing or empty."""
    missing: list[str] = []
    for name in _REQUIRED_VARS:
        if not os.getenv(name):  # empty string also treated as missing
            missing.append(name)
    return missing


config_router = APIRouter(prefix="/config", tags=["config"])  # Exported for app.main


def get_sanitized_env_snapshot(max_val_len: int = 200) -> Dict[str, str]:
    """Return a sanitized environment snapshot for safe diagnostics.

    Rules:
    - Include keys with allowed prefixes: PG_, RAG_, OLLAMA_, CORS_, EMBED_, ASYN
    - Always allow explicit keys (currently SUPABASE_URL)
    - Exclude keys containing common secret markers: KEY, TOKEN, SECRET, PASS, PASSWORD
    - Truncate long values to `max_val_len` and suffix with '...'
    """
    allow_prefixes = (
        "PG_",
        "RAG_",
        "OLLAMA_",
        "CORS_",
        "EMBED_",
        "ASYN",
    )
    allow_explicit = {"SUPABASE_URL"}
    deny_markers = ("KEY", "TOKEN", "SECRET", "PASS", "PASSWORD")

    def _allowed_key(k: str) -> bool:
        kup = k.upper()
        if any(m in kup for m in deny_markers):
            return False
        if kup in allow_explicit:
            return True
        return any(kup.startswith(p) for p in allow_prefixes)

    def _sanitize_val(v: str) -> str:
        if v is None:
            return ""
        if len(v) > max_val_len:
            return v[: max_val_len - 3] + "..."
        return v

    snapshot: Dict[str, str] = {}
    for k, v in os.environ.items():
        if _allowed_key(k):
            snapshot[k] = _sanitize_val(str(v))
    return snapshot


@config_router.get("/env")
def get_env_snapshot() -> Dict[str, object]:  # pragma: no cover - simple pass-through
    """Return a filtered snapshot of environment (non-secret values)."""
    snapshot = get_sanitized_env_snapshot()
    return {"env": snapshot, "missing": validate_required_env()}


@config_router.get("/required")
def get_required() -> Dict[str, object]:
    return {"required": list(_REQUIRED_VARS), "missing": validate_required_env()}
