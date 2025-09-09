"""Family service abstraction with DI (in-memory or Postgres).

Selection logic (see `deps.get_family_service`). This isolates FastAPI router
from concrete persistence (enables RLS / masking via DB policies when active).
"""

from __future__ import annotations

import os
from typing import Any, Optional

from .context import FAMILY_STORE, Person, infer_grade_band

try:  # optional
    from .pg_repo import PgFamilyRepo  # type: ignore
except Exception:  # pragma: no cover
    PgFamilyRepo = None  # type: ignore


class BaseFamilyService:
    def list_people(self) -> list[dict[str, Any]]: ...  # noqa: D401
    def upsert_person(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def get_person(self, pid: str) -> Optional[dict[str, Any]]: ...
    def add_guardian(self, guardian_id: str, child_id: str) -> None: ...
    def tutoring_guardrails(self, child_id: str) -> dict[str, Any]: ...
    def add_health_metric(
        self, entity_id: str, metric: str, value: Any, unit: Optional[str]
    ) -> dict[str, Any] | None: ...
    def list_bucket_items(
        self, entity_id: str, bucket_type: str, limit: int = 50
    ) -> list[dict[str, Any]]: ...
    def list_buckets(self, entity_id: str) -> dict[str, int]: ...
    def add_bucket_item(
        self, entity_id: str, bucket_type: str, item: dict[str, Any]
    ) -> dict[str, Any]: ...
    def add_artifact(
        self,
        entity_id: str,
        kind: str,
        title: str,
        tags: list[str],
        meta: dict[str, Any],
        content_ref: Optional[str],
    ): ...
    def list_artifacts(
        self, entity_id: Optional[str], tag: Optional[str], kind: Optional[str], limit: int
    ) -> list[dict[str, Any]]: ...


class InMemoryFamilyService(BaseFamilyService):
    def list_people(self) -> list[dict[str, Any]]:
        return [p.__dict__ for p in FAMILY_STORE.list_people()]

    def upsert_person(self, data: dict[str, Any]) -> dict[str, Any]:
        p = Person(
            id=data["id"],
            name=data["name"],
            age=data["age"],
            roles=data.get("roles", []),
            meta=data.get("meta", {}),
        )
        FAMILY_STORE.upsert_person(p)
        return p.__dict__

    def get_person(self, pid: str) -> Optional[dict[str, Any]]:
        p = FAMILY_STORE.get_person(pid)
        return p.__dict__ if p else None

    def add_guardian(self, guardian_id: str, child_id: str) -> None:
        FAMILY_STORE.add_guardian(guardian_id, child_id)

    def tutoring_guardrails(self, child_id: str) -> dict[str, Any]:
        return FAMILY_STORE.tutoring_guardrails(child_id)

    def add_health_metric(self, entity_id: str, metric: str, value: Any, unit: Optional[str]):
        return FAMILY_STORE.add_health_metric(entity_id, metric, value, unit)

    def list_bucket_items(
        self, entity_id: str, bucket_type: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        return FAMILY_STORE.list_bucket_items(entity_id, bucket_type, limit=limit)

    def list_buckets(self, entity_id: str) -> dict[str, int]:
        return FAMILY_STORE.list_buckets(entity_id)

    def add_bucket_item(
        self, entity_id: str, bucket_type: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        return FAMILY_STORE.add_bucket_item(entity_id, bucket_type, item)

    def add_artifact(
        self,
        entity_id: str,
        kind: str,
        title: str,
        tags: list[str],
        meta: dict[str, Any],
        content_ref: Optional[str],
    ) -> dict[str, Any]:
        return FAMILY_STORE.add_artifact(entity_id, kind, title, tags, meta, content_ref)

    def list_artifacts(
        self, entity_id: Optional[str], tag: Optional[str], kind: Optional[str], limit: int
    ):
        return FAMILY_STORE.list_artifacts(entity_id=entity_id, tag=tag, kind=kind, limit=limit)


class PgFamilyService(BaseFamilyService):
    def __init__(self, dsn: str):
        if not PgFamilyRepo:  # pragma: no cover
            raise RuntimeError("pg repo unavailable (psycopg2 missing)")
        self.repo = PgFamilyRepo(dsn)
        self.dsn = dsn

    def _user(self, user_id: Optional[str]) -> str:
        return user_id or os.getenv("DEFAULT_FAMILY_USER", "charles")

    def list_people(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:  # RLS enforced
        try:
            rows = self.repo.list_people(app_user=user_id)
        except Exception:
            return []
        out: list[dict[str, Any]] = []
        for r in rows:
            meta = r.get("meta") or {}
            roles = meta.get("roles", []) if isinstance(meta, dict) else []
            out.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "age": r["age"],
                    "grade_band": r["grade_band"],
                    "roles": roles,
                    "meta": meta,
                }
            )
        return out

    def upsert_person(self, data: dict[str, Any], user_id: Optional[str] = None) -> dict[str, Any]:
        # embed roles into meta since table lacks column
        meta = data.get("meta", {}).copy()
        if data.get("roles"):
            meta["roles"] = data["roles"]
        record = {
            "id": data["id"],
            "name": data["name"],
            "age": data["age"],
            "grade_band": infer_grade_band(data["age"]),
            "last_name": None,
            "birthdate": None,
            "household_id": None,
            "meta": meta,
        }
        self.repo.upsert_person(record, app_user=user_id)
        return {**record, "roles": meta.get("roles", [])}

    def get_person(self, pid: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        people = self.list_people(user_id=user_id)
        for p in people:
            if p["id"] == pid:
                return p
        return None

    def add_guardian(self, guardian_id: str, child_id: str, user_id: Optional[str] = None) -> None:
        self.repo.add_guardian(guardian_id, child_id, app_user=user_id)

    def tutoring_guardrails(self, child_id: str) -> dict[str, Any]:
        p = self.get_person(child_id)
        if not p:
            return {"grade_band": None, "policy": "unknown_child"}
        return {
            "grade_band": p["grade_band"],
            "policy": f"child_guardrail_{p['grade_band']}",
            "age": p["age"],
        }

    # Buckets & health metrics: for now not persisted in PG service (fallback to no-op / empty)
    def add_health_metric(self, entity_id: str, metric: str, value: Any, unit: Optional[str]):
        # could map to family_health_metrics via repo
        try:
            self.repo.add_health_metric(entity_id, metric, value, unit, app_user=None)
            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}

    def list_bucket_items(
        self, entity_id: str, bucket_type: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        # Not yet persisted -> empty
        return []

    def list_buckets(self, entity_id: str) -> dict[str, int]:
        return {}

    def add_bucket_item(
        self, entity_id: str, bucket_type: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        return {"error": "not_implemented_pg_bucket"}

    def add_artifact(
        self,
        entity_id: str,
        kind: str,
        title: str,
        tags: list[str],
        meta: dict[str, Any],
        content_ref: Optional[str],
    ):
        art = {
            "id": f"art-{entity_id}-{abs(hash(title)) % 999999}",
            "entity_id": entity_id,
            "kind": kind,
            "title": title,
            "tags": tags,
            "content_ref": content_ref,
            "meta": meta,
            "created_ts": 0,
        }
        try:
            self.repo.add_artifact(art, app_user=None)
        except Exception:
            pass
        return art

    def list_artifacts(
        self, entity_id: Optional[str], tag: Optional[str], kind: Optional[str], limit: int
    ):
        rows = self.repo.list_artifacts(limit=limit, app_user=None)
        out = []
        for r in rows:
            if entity_id and r["entity_id"] != entity_id:
                continue
            if tag and (tag not in (r.get("tags") or [])):
                continue
            if kind and r.get("kind") != kind:
                continue
            out.append(
                {
                    "id": r["id"],
                    "entity_id": r["entity_id"],
                    "kind": r["kind"],
                    "title": r["title"],
                    "tags": r.get("tags") or [],
                    "meta": r.get("meta") or {},
                    "content_ref": r.get("content_ref"),
                    "created_ts": (
                        int(r.get("created_ts").timestamp() * 1000)
                        if hasattr(r.get("created_ts"), "timestamp")
                        else int(r.get("created_ts") or 0)
                    ),
                }
            )
        return out


_CACHED_SERVICE: Optional[BaseFamilyService] = None


def get_service() -> BaseFamilyService:
    global _CACHED_SERVICE
    if _CACHED_SERVICE:
        return _CACHED_SERVICE
    dsn = os.getenv("FAMILY_PG_DSN")
    if dsn and PgFamilyRepo:
        try:
            _CACHED_SERVICE = PgFamilyService(dsn)
            return _CACHED_SERVICE
        except Exception:
            pass
    _CACHED_SERVICE = InMemoryFamilyService()
    return _CACHED_SERVICE
