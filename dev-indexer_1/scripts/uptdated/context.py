"""Clean in-memory family context (factual, deterministic)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import threading


@dataclass(frozen=True)
class Person:
    id: str
    full_name: str
    birth_year: Optional[int] = None
    traits: Tuple[str, ...] = ()
    last_name: Optional[str] = None
    age: Optional[int] = None
    birthdate: Optional[str] = None
    roles: Tuple[str, ...] = ()
    household_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Household:
    id: str
    address: str
    type: str
    members: Tuple[str, ...] = ()
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Pet:
    id: str
    name: str
    species: str
    age: Optional[int] = None
    breed: Optional[str] = None
    household_id: Optional[str] = None


@dataclass(frozen=True)
class Relationship:
    from_id: str
    to_id: str
    kind: str
    legal: bool = False


@dataclass(frozen=True)
class Artifact:
    id: str
    entity_id: str
    kind: str
    title: str
    tags: Tuple[str, ...] = ()
    content_ref: Optional[str] = None


class FamilyStore:
    def __init__(self) -> None:
        self._people: Dict[str, Person] = {}
        self._relationships: List[Relationship] = []
        self._artifacts: List[Artifact] = []
        self._households: Dict[str, Household] = {}
        self._pets: Dict[str, Pet] = {}
        self._buckets: Dict[str, Dict[str, List[dict]]] = {}
        self._seeded = False
        self._lock = threading.Lock()

    def seed(self) -> None:
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._households.update({
                "ripley_log_home": Household(
                    id="ripley_log_home", address="Ripley, WV", type="primary_residence",
                    members=("charles", "nancy", "willow", "chase"), meta={"purchased_year": 2024}),
                "cottageville_rental": Household(
                    id="cottageville_rental", address="Cottageville, WV", type="rental_unit", members=(),
                    meta={"intended_for": "amy_family"}),
            })
            legacy = {
                "charles_bowen": Person("charles_bowen", "Charles Bowen", 1976, ("prior_military", "retired"), last_name="Bowen", roles=("patriarch", "grandparent", "guardian"), household_id="ripley_log_home"),
                "nancy_bowen": Person("nancy_bowen", "Nancy Bowen", 1975, ("planner",), last_name="Bowen", roles=("matriarch", "grandparent", "guardian"), household_id="ripley_log_home"),
                "willow_bowen": Person("willow_bowen", "Willow Bowen", None, (), last_name="Bowen", age=5, roles=("child",), household_id="ripley_log_home"),
                "chase_bowen": Person("chase_bowen", "Chase Bowen", 2007, (), last_name="Bowen", age=18, roles=("young_adult",), household_id="ripley_log_home", meta={"employment": "Marathon Oil (barge)"}),
                "tracey_bowen": Person("tracey_bowen", "Tracey Bowen"),
                "chloe_bowen": Person("chloe_bowen", "Chloe Bowen"),
                "sierra_bowen": Person("sierra_bowen", "Sierra Bowen"),
            }
            new = {
                "charles": Person("charles", "Charles Bowen", 1976, ("prior_military", "retired"), last_name="Bowen", age=49, birthdate="1976-02-16", roles=("patriarch", "grandparent", "guardian"), household_id="ripley_log_home"),
                "nancy": Person("nancy", "Nancy Bowen", 1975, ("planner",), last_name="Bowen", age=50, birthdate="1975-06-18", roles=("matriarch", "grandparent", "guardian"), household_id="ripley_log_home"),
                "tracey": Person("tracey", "Tracey", None, (), age=30, roles=("parent",), meta={"maiden_last_known": None}),
                "sierra": Person("sierra", "Sierra", None, (), age=28, roles=("parent",)),
                "chloe": Person("chloe", "Chloe", None, (), age=32, roles=("parent",), meta={"married_name": "Mullins", "country": "Italy"}),
                "chase": Person("chase", "Chase Bowen", 2007, (), last_name="Bowen", age=18, roles=("young_adult",), household_id="ripley_log_home", meta={"employment": "Marathon Oil (barge)"}),
                "willow": Person("willow", "Willow", None, (), age=5, roles=("child",), household_id="ripley_log_home"),
                "remington": Person("remington", "Remington", None, (), age=3, roles=("grandchild",)),
                "josiah": Person("josiah", "Josiah", None, (), age=4, roles=("grandchild",)),
                "levi": Person("levi", "Levi", None, (), age=2, roles=("grandchild",)),
                "layla": Person("layla", "Layla", None, (), age=1, roles=("grandchild",)),
                "cyrus": Person("cyrus", "Cyrus Bowen", None, (), last_name="Bowen", age=0, roles=("grandchild",), meta={"initials_pattern": "C.B."}),
                "amy": Person("amy", "Amy Williams", None, (), last_name="Williams", age=0, roles=("aunt",), meta={"note": "Age not provided; set 0 placeholder"}),
                "connor": Person("connor", "Connor Mallory", None, (), last_name="Mallory", age=14, roles=("cousin",), meta={"school": "Ripley Middle"}),
                "bella": Person("bella", "Bella Mallory", None, (), last_name="Mallory", age=12, roles=("cousin",), meta={"school": "Ripley Middle"}),
                "scottie": Person("scottie", "Scottie", None, (), age=0, roles=("partner",), meta={"note": "Age unknown placeholder"}),
                "justin": Person("justin", "Justin Mullins", None, (), last_name="Mullins", age=0, roles=("inlaw",), meta={"country": "Italy"}),
                "jake": Person("jake", "Jake Brooks", None, (), last_name="Brooks", age=0, roles=("inlaw",)),
                "emmy": Person("emmy", "Emmy", None, (), age=0, roles=("former_partner",), meta={"note": "former relationship with Chase"}),
            }
            self._people.update(legacy)
            for pid, p in new.items():
                if pid not in self._people:
                    self._people[pid] = p
            self._relationships.extend([
                Relationship("charles_bowen", "willow_bowen", "guardian_of", True),
                Relationship("nancy_bowen", "willow_bowen", "guardian_of", True),
                Relationship("charles_bowen", "chase_bowen", "parent_of"),
                Relationship("nancy_bowen", "chase_bowen", "parent_of"),
                Relationship("charles", "willow", "guardian_of", True),
                Relationship("nancy", "willow", "guardian_of", True),
            ])
            self._artifacts.extend([
                Artifact(id="art_note_willow_school", entity_id="willow_bowen", kind="note", title="School enrollment 2024", tags=("education", "enrollment"), content_ref="sha256:willow_enrollment_v1"),
                Artifact(id="art_doc_chase_sports", entity_id="chase_bowen", kind="document", title="Soccer practice schedule", tags=("sports", "schedule"), content_ref="sha256:chase_soccer_sched_v1"),
                Artifact(id="art_note_household_guardianship", entity_id="charles_bowen", kind="note", title="Guardianship confirmation", tags=("legal", "guardianship"), content_ref="sha256:guardianship_doc_ref"),
                Artifact(id="art_doc_willow_reading_fall_2025", entity_id="willow", kind="document", title="Willow Fall 2025 Reading Assessment", tags=("reading", "assessment", "2025", "fall"), content_ref="doc:willow-reading-fall-2025"),
                Artifact(id="art_media_willow_science_volcano_photo", entity_id="willow", kind="media", title="Willow Science Project Volcano Photo", tags=("science", "project", "photo"), content_ref="img:willow-volcano-project"),
            ])
            self._buckets["willow_bowen"] = {"health": [{"metric": "height_cm", "value": 122, "unit": ""}]}
            self._buckets["chase_bowen"] = {"health": [{"metric": "height_cm", "value": 170, "unit": ""}]}
            self._buckets["willow"] = {"health": [
                {"metric": "reading_score", "value": 92, "unit": ""},
                {"metric": "height_in", "value": 50, "unit": "in"},
            ]}
            self._buckets["chase"] = {"health": [
                {"metric": "gpa", "value": 3.6, "unit": ""},
                {"metric": "height_in", "value": 66, "unit": "in"},
            ]}
            self._pets.update({
                "hershey": Pet("hershey", "Hershey", "dog", age=12, breed="chocolate lab", household_id="ripley_log_home"),
                "gunner": Pet("gunner", "Gunner", "dog", age=7, breed="aussie doodle", household_id="ripley_log_home"),
                "nova": Pet("nova", "Nova", "dog", age=1, breed="pitbull", household_id="ripley_log_home"),
                "alex": Pet("alex", "Alex", "cat", age=0, household_id="ripley_log_home"),
                "daquan": Pet("daquan", "Daquan", "cat", age=0, household_id="ripley_log_home"),
                "precious": Pet("precious", "Precious", "cat", age=0, household_id="ripley_log_home"),
            })
            self._seeded = True

    # Queries
    def list_artifacts(self, *, limit: int = 100) -> List[dict]:
        return [a.__dict__ for a in self._artifacts[:limit]]

    def relationships_for(self, person_id: str) -> List[Relationship]:
        return [r for r in self._relationships if r.from_id == person_id or r.to_id == person_id]

    def guardians_of(self, child_id: str) -> List[str]:
        return [r.from_id for r in self._relationships if r.kind == "guardian_of" and r.to_id == child_id and r.legal]

    def get_person(self, pid: str) -> Optional[Person]:
        return self._people.get(pid)

    def get_household(self, hid: str) -> Optional[Household]:
        return self._households.get(hid)

    def list_pets(self, household_id: Optional[str] = None) -> List[dict]:
        pets = list(self._pets.values())
        if household_id:
            pets = [p for p in pets if p.household_id == household_id]
        return [p.__dict__ for p in pets]

    def list_households(self) -> List[dict]:
        return [h.__dict__ for h in self._households.values()]


FAMILY_STORE = FamilyStore()


def ensure_seed() -> None:
    FAMILY_STORE.seed()
