"""Structured JSON event log (SDD §7.1).

EventLog is the single record type written for every agent decision, inter-agent
message, and environment state change. Sinks persist it; the PostgreSQL sink is
added in Phase 6.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
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
    inputs: dict[str, Any] = Field(default_factory=dict)
    plan_selected: str
    reasoning: str
    action: str
    # Structured decision internals for the dashboard (additive, optional — the FR
    # constraint checker reads none of these, so existing call sites are unaffected).
    confidence: float | None = None
    novelty: float | None = None
    features: list[float] | None = None
    feature_names: list[str] | None = None
    votes: dict[str, str] | None = None  # voter_id -> ACCEPT/REJECT
    vote_rationale: dict[str, str] | None = None


class EventLog(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    lamport_ts: int
    wall_ms: float
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent_id: str
    agent_type: str
    segment: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
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


class StructlogSink(EventSink):
    """Emits each event as a structured JSON log line (production default)."""

    def __init__(self) -> None:
        import structlog

        self._log = structlog.get_logger("cdmas.events")

    async def write(self, event: EventLog) -> None:
        self._log.info(event.event_type.value, **event.model_dump(mode="json"))
