"""Application factory (transitional).

Phase 1 decomposition for task 5: provide a `create_app()` function so
future refactors can progressively move logic out of `app.main` without
changing external ASGI entrypoints (e.g. `uvicorn app.main:app`).

Subsequent phases will:
  - Extract core endpoint groups into dedicated routers
  - Move audio bootstrap + dynamic imports into `bootstrap/audio.py`
  - Slim `app.main` down to an import + `app = create_app()` pattern
"""
from __future__ import annotations

from fastapi import FastAPI

def create_app() -> FastAPI:  # pragma: no cover - thin delegator
    from app import main as _legacy  # local import to avoid circulars during refactor

    return _legacy.app
