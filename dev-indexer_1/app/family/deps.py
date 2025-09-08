from __future__ import annotations
import os
from .service import InMemoryFamilyService, BaseFamilyService


_svc: BaseFamilyService | None = None


def get_family_service() -> BaseFamilyService:
    global _svc
    if _svc is None:
        # Future: switch to Postgres-backed if DSN present
        _svc = InMemoryFamilyService()
    return _svc


def get_family_user() -> str:
    # Stub user for now; could extract from auth header/session in the future
    return os.getenv("FAMILY_USER", "dev-user")
