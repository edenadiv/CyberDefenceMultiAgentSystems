"""Voting payloads for quarantine escalation (SDD §3.2.4)."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import ResponseType, Segment, VoteDecision


class VoteRequest(BaseModel):
    vote_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal: ResponseType
    target_segment: Segment
    threat_id: str
    severity: float = Field(ge=0.0, le=1.0)
    deadline: datetime


class VoteResponse(BaseModel):
    vote_id: str
    voter_id: str
    decision: VoteDecision
    rationale: str = ""
