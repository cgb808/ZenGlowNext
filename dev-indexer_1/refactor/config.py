"""Configuration helpers: backward compatibility, validation, sanitized snapshot.

Responsibilities:
1. Backward compatibility shim for renamed environment variables.
2. Startup validation of required (non-secret) environment variables.
3. Sanitized environment snapshot endpoint support.

Secrets are intentionally excluded from snapshots based on heuristic name matching.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from fastapi import APIRouter

# Old -> New env var mapping for backward compatibility
_BACKCOMPAT_MAP: Dict[str, str] = {
    "FUSION_LTR_WEIGHT": "RAG_FUSION_LTR_WEIGHT",
    "FUSION_CONCEPTUAL_WEIGHT": "RAG_FUSION_CONCEPTUAL_WEIGHT",
    "RAG_TOP_K": "RAG_TOP_K_DEFAULT",
}

# Non-secret required env vars (fail-fast if missing in STRICT mode)
STRICT_ENV = os.getenv("STRICT_ENV", "true").lower() == "true"
if STRICT_ENV:
    REQUIRED_ENV: List[str] = [
        "DATABASE_URL",
        "REDIS_HOST",
        "REDIS_PORT",
    ]
else:
    # Minimal set – allow degraded startup where Redis is optional and DB may be swapped later
    REQUIRED_ENV = [
        "DATABASE_URL",
    ]

# Heuristic substrings that mark a var as secret (excluded from snapshot)
_SECRET_MARKERS = ["KEY", "SECRET", "PASS", "TOKEN", "PASSWORD"]


def apply_backward_compat_env() -> List[Tuple[str, str]]:
    """Apply backward compatibility mapping (source -> target).

    Returns list of (source, target) pairs applied.
    """
    applied: List[Tuple[str, str]] = []
    for old, new in _BACKCOMPAT_MAP.items():
        if old in os.environ and new not in os.environ:
            os.environ[new] = os.environ[old]
            applied.append((old, new))
    return applied


def validate_required_env(fail_fast: bool = True) -> List[str]:
    """Validate required environment variables present.

    Returns list of missing vars. Raises RuntimeError if fail_fast and any missing.
    """
    missing = [v for v in REQUIRED_ENV if not os.getenv(v)]
    if fail_fast and missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return missing


def _is_secret_name(name: str) -> bool:
    up = name.upper()
    return any(marker in up for marker in _SECRET_MARKERS)


def get_sanitized_env_snapshot() -> Dict[str, str]:
    """Return sanitized view of env for ops: excludes secrets & internal noise.

    Strategy:
      * Include vars starting with RAG_, OLLAMA_, REDIS_, PG_, DATABASE_URL, CHROMA_, SUPABASE_URL (not keys).
      * Exclude anything whose name contains secret markers (KEY, SECRET, PASS, TOKEN, PASSWORD) except allowlist of SUPABASE_URL.
    """
    snapshot: Dict[str, str] = {}
    allow_prefixes = (
        "RAG_",
        "OLLAMA_",
        "REDIS_",
        "PG_",
        "DATABASE_URL",
        "CHROMA_",
        "SUPABASE_URL",
    )
    for k, v in os.environ.items():
        if not k.startswith(allow_prefixes):
            continue
        if k == "SUPABASE_URL":  # allowed explicitly
            snapshot[k] = v
            continue
        if _is_secret_name(k):
            continue
        # truncate long values for readability (e.g. URLs fine, embeddings not expected here)
        if len(v) > 200:
            v_display = v[:197] + "..."
        else:
            v_display = v
        snapshot[k] = v_display
    return snapshot


# FastAPI router for config endpoints
config_router: APIRouter = APIRouter(prefix="/config", tags=["config"])


@config_router.get("/env")
def get_env_config() -> Dict[str, Dict[str, str]]:  # pragma: no cover - simple accessor
    """Return sanitized environment snapshot for operational visibility."""
    return {"env": get_sanitized_env_snapshot()}


__all__ = [
    "apply_backward_compat_env",
    "validate_required_env",
    "get_sanitized_env_snapshot",
    "config_router",
]
