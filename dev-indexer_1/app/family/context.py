from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


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

    def __init__(self) -> None:
        self.people = {}
        self.events = []

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


FAMILY_STORE = _Store()


def ensure_seed() -> None:
    if FAMILY_STORE.people:
        return
    FAMILY_STORE.upsert_person(Person(id="p1", name="Alex", age=12, roles=["student"]))
    FAMILY_STORE.upsert_person(Person(id="p2", name="Sam", age=38, roles=["guardian"]))
