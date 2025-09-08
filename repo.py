"""Repository interfaces (protocols) for family context.

Concrete persistence backends (e.g. Postgres, Timescale) can implement these
to replace the current in-memory store. Swapping is done by wiring dependency
injection at FastAPI startup.
"""
from __future__ import annotations
from typing import Protocol, Iterable, Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Artifact:
    id: str
    entity_id: str  # person or pet id
    kind: str       # document | media | note
    title: str
    tags: List[str] = field(default_factory=list)
    content_ref: Optional[str] = None  # external storage reference / hash
    meta: Dict[str, Any] = field(default_factory=dict)
    created_ts: int = 0


class PersonRepository(Protocol):
    def upsert(self, person: Any) -> Any: ...  # person model
    def get(self, person_id: str) -> Optional[Any]: ...
    def list(self) -> Iterable[Any]: ...


class RelationshipRepository(Protocol):
    def add_legal_guardian(self, guardian_id: str, child_id: str) -> None: ...
    def guardians_of(self, child_id: str) -> List[Any]: ...
    def children_of(self, guardian_id: str) -> List[Any]: ...


class BucketRepository(Protocol):
    def list_buckets(self, entity_id: str) -> Dict[str, int]: ...
    def add_bucket_item(self, entity_id: str, bucket_type: str, item: Dict[str, Any]) -> Dict[str, Any]: ...
    def list_bucket_items(self, entity_id: str, bucket_type: str, limit: int = 50) -> List[Dict[str, Any]]: ...


class ArtifactRepository(Protocol):
    def add_artifact(self, artifact: Artifact) -> Artifact: ...
    def list_artifacts(self, entity_id: Optional[str] = None, tag: Optional[str] = None, kind: Optional[str] = None, limit: int = 100) -> List[Artifact]: ...
