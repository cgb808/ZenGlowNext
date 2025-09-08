"""FastAPI dependency providers for family context DI."""
from __future__ import annotations
from fastapi import Request, Depends
from .service import get_service, BaseFamilyService


def get_family_service() -> BaseFamilyService:
    return get_service()


def get_family_user(request: Request) -> str:
    return request.headers.get('X-Family-User', 'charles')
