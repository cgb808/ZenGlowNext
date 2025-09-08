"""Family context domain model and in-memory store.

Scope (initial):
- Track people (name, age, grade_band, roles).
- Track relationships (guardian -> child) minimal.
- Provide resolution helpers for tutoring guardrails.

Persisting: Future step (Timescale / Postgres). For now ephemeral so API usable
immediately without migrations. Replace backing store with repository later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any, Union
import threading
import time
import json
import pathlib

GradeBand = Literal["preK","K","1-2","3-5","6-8","9-12","adult"]

def infer_grade_band(age: int) -> GradeBand:
    if age < 5:
        return "preK"
    if age == 5:
        return "K"
    if 6 <= age <= 8:
        return "1-2"
    if 9 <= age <= 11:
        return "3-5"
    if 12 <= age <= 13:
        return "6-8"
    if 14 <= age <= 18:
        return "9-12"
    return "adult"

@dataclass
class Person:
    id: str
    name: str
    age: int
    roles: List[str] = field(default_factory=list)
    grade_band: GradeBand = field(init=False)
    last_name: Optional[str] = None
    birthdate: Optional[str] = None  # ISO (yyyy-mm-dd) when stored (adults only here)
    household_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.grade_band = infer_grade_band(self.age)

@dataclass
class Relationship:
    guardian_id: str
    child_id: str
    kind: Literal["guardian"] = "guardian"
    legal: bool = True  # default legal guardianship (explicit flag for persistence)

class FamilyStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._people: Dict[str, Person] = {}
        self._relationships: List[Relationship] = []
        self._events: List[Dict[str, Any]] = []  # timeline markers (ephemeral)
        self._households: Dict[str, Dict[str, Any]] = {}
        self._pets: Dict[str, Dict[str, Any]] = {}
        # entity_id -> bucket_type -> list[item]
        self._buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        # artifacts (separate from simple bucket items, normalized for fine-tune extraction)
        self._artifacts: List[Dict[str, Any]] = []

    # People CRUD
    def upsert_person(self, p: Person) -> Person:
        with self._lock:
            self._people[p.id] = p
            return p

    def get_person(self, pid: str) -> Optional[Person]:
        return self._people.get(pid)

    def list_people(self) -> List[Person]:
        return list(self._people.values())

    # Relationships
    def add_guardian(self, guardian_id: str, child_id: str, legal: bool = True) -> None:
        with self._lock:
            if guardian_id not in self._people or child_id not in self._people:
                raise ValueError("unknown person id")
            rel = Relationship(guardian_id=guardian_id, child_id=child_id, legal=legal)
            if rel not in self._relationships:
                self._relationships.append(rel)

    def children_of(self, guardian_id: str) -> List[Person]:
        return [self._people[r.child_id] for r in self._relationships if r.guardian_id == guardian_id]

    def guardians_of(self, child_id: str) -> List[Person]:
        return [self._people[r.guardian_id] for r in self._relationships if r.child_id == child_id]

    # Timeline markers (tutoring sessions etc.)
    def record_event(self, kind: str, subject: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        evt = {
            "ts": int(time.time()*1000),
            "kind": kind,
            "subject": subject,
            "meta": meta,
        }
        with self._lock:
            self._events.append(evt)
        return evt

    def list_events(self, kind: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        evts = self._events if kind is None else [e for e in self._events if e["kind"] == kind]
        return list(reversed(evts))[:limit]

    # Guardrail helper
    def tutoring_guardrails(self, target_id: str) -> Dict[str, Any]:
        p = self.get_person(target_id)
        if not p:
            return {"grade_band": None, "policy": "unknown_child"}
        return {"grade_band": p.grade_band, "policy": f"child_guardrail_{p.grade_band}", "age": p.age}

    # Households ---------------------------------------------------------
    def upsert_household(self, hid: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._households[hid] = data

    def list_households(self) -> List[Dict[str, Any]]:
        return list(self._households.values())

    # Pets ---------------------------------------------------------------
    def upsert_pet(self, pid: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._pets[pid] = data

    def list_pets(self) -> List[Dict[str, Any]]:
        return list(self._pets.values())

    # Buckets (health, documents, media) --------------------------------
    def list_buckets(self, entity_id: str) -> Dict[str, int]:
        with self._lock:
            buckets = self._buckets.get(entity_id, {})
            return {k: len(v) for k, v in buckets.items()}

    def add_bucket_item(self, entity_id: str, bucket_type: str, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            buckets = self._buckets.setdefault(entity_id, {})
            lst = buckets.setdefault(bucket_type, [])
            new_item = {"id": f"{bucket_type}-{len(lst)+1}", "ts": int(time.time()*1000), **item}
            lst.append(new_item)
            return new_item

    def list_bucket_items(self, entity_id: str, bucket_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            buckets = self._buckets.get(entity_id, {})
            items = list(reversed(buckets.get(bucket_type, [])))
            return items[:limit]

    def add_health_metric(self, entity_id: str, metric: str, value: Union[int, float, str], unit: Optional[str]) -> Dict[str, Any]:
        return self.add_bucket_item(entity_id, "health", {"kind": "metric", "metric": metric, "value": value, "unit": unit})

    # Artifacts -----------------------------------------------------------
    def add_artifact(self, entity_id: str, kind: str, title: str, tags: List[str], meta: Dict[str, Any], content_ref: Optional[str]) -> Dict[str, Any]:
        art = {
            "id": f"art-{len(self._artifacts)+1}",
            "entity_id": entity_id,
            "kind": kind,
            "title": title,
            "tags": tags,
            "meta": meta,
            "content_ref": content_ref,
            "created_ts": int(time.time()*1000),
        }
        with self._lock:
            self._artifacts.append(art)
        return art

    def list_artifacts(self, entity_id: Optional[str] = None, tag: Optional[str] = None, kind: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        arts = self._artifacts
        if entity_id:
            arts = [a for a in arts if a["entity_id"] == entity_id]
        if tag:
            arts = [a for a in arts if tag in a.get("tags", [])]
        if kind:
            arts = [a for a in arts if a.get("kind") == kind]
        return list(reversed(arts))[:limit]

FAMILY_STORE = FamilyStore()

_SEED_PATH = pathlib.Path(__file__).parent / "seed_data.json"

def ensure_seed():  # pragma: no cover - IO
    if not _SEED_PATH.exists():
        return
    try:
        data = json.loads(_SEED_PATH.read_text())
        # Load core entities only if not already present
        if not FAMILY_STORE.list_people():
            for h in data.get("households", []):
                FAMILY_STORE.upsert_household(h["id"], h)
            for p in data.get("people", []):
                person = Person(
                    id=p["id"], name=p["name"], age=p["age"], roles=p.get("roles", []),
                    last_name=p.get("last_name"), birthdate=p.get("birthdate"),
                    household_id=p.get("household_id"), meta=p.get("meta", {})
                )
                FAMILY_STORE.upsert_person(person)
            for r in data.get("guardians", []):
                try:
                    FAMILY_STORE.add_guardian(r["guardian"], r["child"], legal=r.get("legal", True))
                except Exception:
                    pass
            for pet in data.get("pets", []):
                FAMILY_STORE.upsert_pet(pet["id"], pet)
            # initialize empty buckets
            for ent in list(FAMILY_STORE._people.keys()) + list(FAMILY_STORE._pets.keys()):
                for bucket in ("health","documents","media"):
                    FAMILY_STORE._buckets.setdefault(ent, {}).setdefault(bucket, [])
            # health metrics
            for hm in data.get("health_metrics", []):
                existing = [m for m in FAMILY_STORE._buckets.get(hm["entity_id"], {}).get("health", []) if m.get("metric") == hm["metric"]]
                if not existing:
                    FAMILY_STORE.add_health_metric(hm["entity_id"], hm["metric"], hm["value"], hm.get("unit"))
        # Artifacts load (idempotent)
        if not FAMILY_STORE.list_artifacts() and data.get("artifacts"):
            for a in data["artifacts"]:
                FAMILY_STORE.add_artifact(
                    a["entity_id"], a["kind"], a["title"], a.get("tags", []), a.get("meta", {}), a.get("content_ref")
                )
    except Exception:
        pass
