"""FIPA-ACL message envelope and schema validation (SDD §3.1.1, FR-32)."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


class SchemaViolation(Exception):
    """Raised when an inbound message fails schema validation (FR-32)."""


class ACLMessage(BaseModel):
    msg_id: str = Field(default_factory=lambda: str(uuid4()))
    performative: Performative
    sender: str
    receiver: str  # an agent id, or "BROADCAST"
    topic: Topic
    conversation_id: str | None = None
    reply_by: datetime | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    # Set by the agent on send (per-sender monotonic) for idempotent dedup.
    seq: int = 0
    # Set authoritatively by the bus on publish for total ordering.
    lamport_ts: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def parse_message(raw: str | bytes) -> ACLMessage:
    """Validate an inbound message; raise SchemaViolation on any problem."""
    try:
        return ACLMessage.model_validate_json(raw)
    except ValidationError as exc:
        raise SchemaViolation(str(exc)) from exc
