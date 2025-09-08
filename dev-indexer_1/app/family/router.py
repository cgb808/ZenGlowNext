from __future__ import annotations
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .context import ensure_seed
from .deps import get_family_service, get_family_user
from .service import BaseFamilyService


router = APIRouter(prefix="/family", tags=["family"])

ensure_seed()


class PersonIn(BaseModel):
    id: str
    name: str
    age: int
    roles: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class PersonOut(BaseModel):
    id: str
    name: str
    age: int
    grade_band: str | None = None
    roles: List[str]
    meta: Dict[str, Any]


@router.get("/people", response_model=List[PersonOut])
def list_people(
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return [PersonOut(**p) for p in svc.list_people(user_id=user) if p]


@router.post("/people", response_model=PersonOut)
def upsert_person(
    body: PersonIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    p = svc.upsert_person(
        {
            "id": body.id,
            "name": body.name,
            "age": body.age,
            "roles": body.roles or [],
            "meta": body.meta or {},
        },
        user_id=user,
    )
    # compute grade band best-effort
    gb = None
    try:
        age = int(p.get("age", 0))
        gb = "K-5" if age <= 11 else ("6-8" if age <= 14 else ("9-12" if age <= 18 else None))
    except Exception:
        pass
    p.setdefault("grade_band", gb)
    return PersonOut(**p)


@router.get("/people/{pid}", response_model=PersonOut)
def get_person(
    pid: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    p = svc.get_person(pid, user_id=user) if hasattr(svc, "get_person") else None
    if not p:
        raise HTTPException(status_code=404, detail="person not found")
    return PersonOut(**p)


@router.post("/relationships/guardian")
def add_guardian(
    guardian_id: str,
    child_id: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    try:
        if hasattr(svc, "add_guardian"):
            svc.add_guardian(guardian_id, child_id, user_id=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/tutoring/guardrails/{child_id}")
def tutoring_guardrails(
    child_id: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return svc.tutoring_guardrails(child_id)


class EventIn(BaseModel):
    kind: str
    subject: str
    meta: Dict[str, Any] = {}


@router.post("/events")
def record_event(evt: EventIn):
    from .context import FAMILY_STORE  # lazy to avoid cycle

    return FAMILY_STORE.record_event(evt.kind, evt.subject, evt.meta)


@router.get("/events")
def list_events(kind: Optional[str] = None, limit: int = 50):
    from .context import FAMILY_STORE  # lazy to avoid cycle

    return {"events": FAMILY_STORE.list_events(kind=kind, limit=limit)}


@router.get("/households")
def list_households():
    # Not yet abstracted in service (rarely used) – still uses in-memory seed if available
    from .context import FAMILY_STORE  # lazy import

    return {"households": []}


@router.get("/pets")
def list_pets():
    return {"pets": []}


@router.get("/buckets/{entity_id}")
def list_buckets(entity_id: str, svc: BaseFamilyService = Depends(get_family_service)):
    return {"entity_id": entity_id, "buckets": {}}


class HealthMetricIn(BaseModel):
    metric: str
    value: Any
    unit: Optional[str] = None


@router.post("/buckets/{entity_id}/health")
def add_health_metric(
    entity_id: str,
    body: HealthMetricIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"ok": True}


class BucketItemIn(BaseModel):
    title: str
    content: Optional[str] = None  # could be text summary or small base64 snippet
    media_type: Optional[str] = None  # e.g., image/png (if present, placeholder stored)
    meta: Dict[str, Any] = {}


@router.post("/buckets/{entity_id}/{bucket_type}")
def add_bucket_item(
    entity_id: str,
    bucket_type: str,
    body: BucketItemIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"ok": True}


@router.get("/buckets/{entity_id}/{bucket_type}")
def list_bucket_items(
    entity_id: str,
    bucket_type: str,
    limit: int = 50,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"items": [], "entity_id": entity_id, "bucket_type": bucket_type}


class ArtifactIn(BaseModel):
    entity_id: str
    kind: str  # document|media|note
    title: str
    tags: List[str] = []
    content_ref: str | None = None
    meta: Dict[str, Any] = {}


@router.post("/artifacts")
def add_artifact(
    body: ArtifactIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"ok": True}


@router.get("/artifacts")
def list_artifacts(
    entity_id: str | None = None,
    tag: str | None = None,
    kind: str | None = None,
    limit: int = 100,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"items": []}
"""FastAPI router exposing family context operations with DI."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .context import ensure_seed
from .deps import get_family_service, get_family_user
from .service import BaseFamilyService

router = APIRouter(prefix="/family", tags=["family"])

ensure_seed()


class PersonIn(BaseModel):
    id: str
    name: str
    age: int
    roles: Optional[list[str]] = None
    meta: Optional[dict[str, Any]] = None


class PersonOut(BaseModel):
    id: str
    name: str
    age: int
    grade_band: str
    roles: list[str]
    meta: dict[str, Any]


@router.get("/people", response_model=list[PersonOut])
def list_people(
    svc: BaseFamilyService = Depends(get_family_service), user: str = Depends(get_family_user)
):
    return [PersonOut(**p) for p in svc.list_people(user_id=user) if p]


@router.post("/people", response_model=PersonOut)
def upsert_person(
    body: PersonIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    p = svc.upsert_person(
        {
            "id": body.id,
            "name": body.name,
            "age": body.age,
            "roles": body.roles or [],
            "meta": body.meta or {},
        },
        user_id=user,
    )
    return PersonOut(**p)


@router.get("/people/{pid}", response_model=PersonOut)
def get_person(
    pid: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    p = svc.get_person(pid, user_id=user) if hasattr(svc, "get_person") else None
    if not p:
        raise HTTPException(404, "person not found")
    return PersonOut(**p)


@router.post("/relationships/guardian")
def add_guardian(
    guardian_id: str,
    child_id: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    try:
        svc.add_guardian(guardian_id, child_id, user_id=user)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.get("/tutoring/guardrails/{child_id}")
def tutoring_guardrails(
    child_id: str,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return svc.tutoring_guardrails(child_id)


class EventIn(BaseModel):
    kind: str
    subject: str
    meta: dict[str, Any] = {}


@router.post("/events")
def record_event(evt: EventIn):
    from .context import FAMILY_STORE  # lazy import to avoid global coupling

    return FAMILY_STORE.record_event(evt.kind, evt.subject, evt.meta)


@router.get("/events")
def list_events(kind: Optional[str] = None, limit: int = 50):
    from .context import FAMILY_STORE

    return {"events": FAMILY_STORE.list_events(kind=kind, limit=limit)}


# Households & Pets ---------------------------------------------------------
@router.get("/households")
def list_households():
    # Not yet abstracted in service (rarely used) – still uses in-memory seed if available
    from .context import FAMILY_STORE  # lazy import to avoid cycle

    return {"households": FAMILY_STORE.list_households()}


@router.get("/pets")
def list_pets():
    from .context import FAMILY_STORE

    return {"pets": FAMILY_STORE.list_pets()}


# Buckets (health, documents, media) ---------------------------------------
@router.get("/buckets/{entity_id}")
def list_buckets(entity_id: str, svc: BaseFamilyService = Depends(get_family_service)):
    return {"buckets": svc.list_buckets(entity_id)}


class HealthMetricIn(BaseModel):
    metric: str
    value: Any
    unit: Optional[str] = None


@router.post("/buckets/{entity_id}/health")
def add_health_metric(
    entity_id: str,
    body: HealthMetricIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return svc.add_health_metric(entity_id, body.metric, body.value, body.unit)


class BucketItemIn(BaseModel):
    title: str
    content: Optional[str] = None  # could be text summary or small base64 snippet
    media_type: Optional[str] = None  # e.g., image/png (if present, placeholder stored)
    meta: dict[str, Any] = {}


@router.post("/buckets/{entity_id}/{bucket_type}")
def add_bucket_item(
    entity_id: str,
    bucket_type: str,
    body: BucketItemIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    if bucket_type not in {"documents", "media"}:
        raise HTTPException(400, "bucket_type must be one of: documents, media")
    return svc.add_bucket_item(entity_id, bucket_type, body.model_dump())


@router.get("/buckets/{entity_id}/{bucket_type}")
def list_bucket_items(
    entity_id: str,
    bucket_type: str,
    limit: int = 50,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"items": svc.list_bucket_items(entity_id, bucket_type, limit=limit)}


# Artifacts ---------------------------------------------------------------
class ArtifactIn(BaseModel):
    entity_id: str
    kind: str  # document|media|note
    title: str
    tags: list[str] = []
    content_ref: str | None = None
    meta: dict[str, Any] = {}


@router.post("/artifacts")
def add_artifact(
    body: ArtifactIn,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return svc.add_artifact(
        body.entity_id, body.kind, body.title, body.tags, body.meta, body.content_ref
    )


@router.get("/artifacts")
def list_artifacts(
    entity_id: str | None = None,
    tag: str | None = None,
    kind: str | None = None,
    limit: int = 100,
    svc: BaseFamilyService = Depends(get_family_service),
    user: str = Depends(get_family_user),
):
    return {"artifacts": svc.list_artifacts(entity_id=entity_id, tag=tag, kind=kind, limit=limit)}
