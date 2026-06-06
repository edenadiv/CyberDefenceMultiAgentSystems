"""Error reply payloads: FAILURE and NOT-UNDERSTOOD (SDD §3.2.5, §3.2.6)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class Failure(BaseModel):
    failure_id: str = Field(default_factory=lambda: str(uuid4()))
    in_reply_to: str
    sender: str
    receiver: str
    reason: str  # TIMEOUT | RESOURCE_UNAVAILABLE | PLAN_PRECONDITION_FAILED
    failed_action: str
    description: str = ""
    fallback_action: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotUnderstood(BaseModel):
    not_understood_id: str = Field(default_factory=lambda: str(uuid4()))
    in_reply_to: str
    sender: str
    receiver: str
    reason: str  # UNKNOWN_PERFORMATIVE | SCHEMA_VIOLATION | MISSING_FIELD
    offending_field: str | None = None
    description: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
