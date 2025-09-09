from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
	import redis  # type: ignore
except Exception:  # pragma: no cover
	redis = None  # type: ignore


router = APIRouter(prefix="/events", tags=["events"])


# Canonical entities
class User(BaseModel):
	id: str
	name: Optional[str] = None
	roles: list[str] = Field(default_factory=list)


class Agent(BaseModel):
	id: str
	specialty: Optional[str] = None
	status: Optional[str] = None


class Device(BaseModel):
	id: str
	type: Optional[str] = None
	location: Optional[str] = None


class Event(BaseModel):
	timestamp: str  # ISO8601; persisted as timestamptz
	eventType: str
	userID: Optional[str] = None
	agentID: Optional[str] = None
	deviceID: Optional[str] = None
	dataPayload: dict[str, Any] = Field(default_factory=dict)

	def to_pubsub(self) -> dict[str, Any]:
		return {
			"timestamp": self.timestamp,
			"eventType": self.eventType,
			"userID": self.userID,
			"agentID": self.agentID,
			"deviceID": self.deviceID,
			"dataPayload": self.dataPayload,
		}


class KnowledgeEdge(BaseModel):
	sourceNode: str
	targetNode: str
	relationshipType: str
	confidence: Optional[float] = None
	explanation: Optional[str] = None
	discoveredBy: Optional[str] = None


def _redis_client():
	if redis is None:  # pragma: no cover
		return None
	host = os.getenv("REDIS_HOST", "localhost")
	port = int(os.getenv("REDIS_PORT", "6379"))
	return redis.StrictRedis(host=host, port=port)


@router.post("/ingest")
async def ingest_event(evt: Event) -> dict[str, Any]:
	"""Accept an Event and publish to Redis Pub/Sub, returning ack.

	Persisting to Postgres/Timescale can be handled by a subscriber worker.
	"""
	payload = evt.to_pubsub()
	published = False
	try:
		r = _redis_client()
		if r is not None:
			# Canonical topic namespace
			topic = f"events:{evt.eventType}"
			r.publish(topic, __import__("json").dumps(payload))
			published = True
	except Exception:
		published = False
	return {"ok": True, "published": published, "eventType": evt.eventType}

