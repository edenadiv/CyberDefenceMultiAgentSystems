"""Structured JSON event log (SDD §7.1).

EventLog is the single record type written for every agent decision, inter-agent
message, and environment state change. Sinks persist it; the PostgreSQL sink is
added in Phase 6.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    ALERT_PUBLISHED = "ALERT_PUBLISHED"
    THREAT_CLASSIFIED = "THREAT_CLASSIFIED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    AUCTION_COMPLETED = "AUCTION_COMPLETED"
    VOTE_CAST = "VOTE_CAST"
    COALITION_FORMED = "COALITION_FORMED"
    AGENT_FAILED = "AGENT_FAILED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


class DecisionTrace(BaseModel):
    inputs: dict = Field(default_factory=dict)
    plan_selected: str
    reasoning: str
    action: str


class EventLog(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    lamport_ts: int
    wall_ms: float
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str
    agent_type: str
    segment: str | None = None
    payload: dict = Field(default_factory=dict)
    latency_ms: int | None = None
    decision_trace: DecisionTrace | None = None


class EventSink(ABC):
    @abstractmethod
    async def write(self, event: EventLog) -> None: ...


class InMemorySink(EventSink):
    def __init__(self) -> None:
        self.events: list[EventLog] = []

    async def write(self, event: EventLog) -> None:
        self.events.append(event)
