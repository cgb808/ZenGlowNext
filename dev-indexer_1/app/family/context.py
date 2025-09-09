from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time


@dataclass
class Person:
    id: str
    name: str
    age: int
    roles: List[str] = field(default_factory=lambda: [])
    meta: Dict[str, Any] = field(default_factory=lambda: {})


class _Store:
    people: Dict[str, Dict[str, Any]]
    events: List[Dict[str, Any]]
    guardians: List[Tuple[str, str]]
    health_metrics: Dict[str, List[Dict[str, Any]]]
    buckets: Dict[str, Dict[str, List[Dict[str, Any]]]]
    artifacts: List[Dict[str, Any]]

    def __init__(self) -> None:
        self.people = {}
        self.events = []
        self.guardians = []
        self.health_metrics = {}
        self.buckets = {}
        self.artifacts = []

    def upsert_person(self, p: Person) -> Dict[str, Any]:
        d = asdict(p)
        self.people[p.id] = d
        return d

    def list_people(self) -> List[Dict[str, Any]]:
        return list(self.people.values())

    def get_person(self, pid: str) -> Dict[str, Any] | None:
        return self.people.get(pid)

    def record_event(self, kind: str, subject: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        evt: Dict[str, Any] = {"kind": kind, "subject": subject, "meta": dict(meta)}
        self.events.append(evt)
        return evt

    def list_events(self, kind: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        items = self.events
        if kind:
            items = [e for e in items if e.get("kind") == kind]
        return items[-limit:]

    # -------- relationships / tutoring guardrails --------
    def add_guardian(self, guardian_id: str, child_id: str) -> None:
        self.guardians.append((guardian_id, child_id))
        self.record_event("add_guardian", child_id, {"guardian_id": guardian_id})

    def tutoring_guardrails(self, child_id: str) -> Dict[str, Any]:
        child = self.get_person(child_id)
        age = (child or {}).get("age") if child else None
        gb = infer_grade_band(age) if isinstance(age, int) else None
        return {"child_id": child_id, "grade_band": gb, "allow": True, "rules": []}

    # ------------------- health metrics -------------------
    def add_health_metric(self, entity_id: str, metric: str, value: Any, unit: Optional[str]):
        entry = {
            "entity_id": entity_id,
            "metric": metric,
            "value": value,
            "unit": unit,
            "ts": int(time.time() * 1000),
        }
        self.health_metrics.setdefault(entity_id, []).append(entry)
        self.record_event("health_metric", entity_id, {"metric": metric})
        return entry

    # ----------------------- buckets ----------------------
    def list_bucket_items(self, entity_id: str, bucket_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.buckets.get(entity_id, {}).get(bucket_type, [])[-limit:]

    def list_buckets(self, entity_id: str) -> Dict[str, int]:
        return {k: len(v) for k, v in self.buckets.get(entity_id, {}).items()}

    def add_bucket_item(self, entity_id: str, bucket_type: str, item: Dict[str, Any]) -> Dict[str, Any]:
        self.buckets.setdefault(entity_id, {}).setdefault(bucket_type, []).append(item)
        self.record_event("bucket_item", entity_id, {"bucket_type": bucket_type})
        return item

    # ---------------------- artifacts ---------------------
    def add_artifact(
        self,
        entity_id: str,
        kind: str,
        title: str,
        tags: List[str],
        meta: Dict[str, Any],
        content_ref: Optional[str],
    ) -> Dict[str, Any]:
        art = {
            "id": f"art-{entity_id}-{abs(hash((title, kind))) % 999999}",
            "entity_id": entity_id,
            "kind": kind,
            "title": title,
            "tags": list(tags),
            "content_ref": content_ref,
            "meta": dict(meta),
            "created_ts": int(time.time() * 1000),
        }
        self.artifacts.append(art)
        self.record_event("artifact", entity_id, {"kind": kind})
        return art

    def list_artifacts(
        self, entity_id: Optional[str], tag: Optional[str], kind: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        items = self.artifacts
        if entity_id:
            items = [a for a in items if a.get("entity_id") == entity_id]
        if tag:
            items = [a for a in items if tag in (a.get("tags") or [])]
        if kind:
            items = [a for a in items if a.get("kind") == kind]
        return items[-limit:]

    # ---------------- households / pets -------------------
    def list_households(self) -> List[Dict[str, Any]]:
        return []

    def list_pets(self) -> List[Dict[str, Any]]:
        return []


FAMILY_STORE = _Store()


def ensure_seed() -> None:
    if FAMILY_STORE.people:
        return
    FAMILY_STORE.upsert_person(Person(id="p1", name="Alex", age=12, roles=["student"]))
    FAMILY_STORE.upsert_person(Person(id="p2", name="Sam", age=38, roles=["guardian"]))


def infer_grade_band(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    try:
        a = int(age)
    except Exception:
        return None
    if a <= 11:
        return "K-5"
    if a <= 14:
        return "6-8"
    if a <= 18:
        return "9-12"
    return None
