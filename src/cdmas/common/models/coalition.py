"""Coalition formation payloads (SDD §4.3)."""

from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import Segment


class CoalitionInvite(BaseModel):
    coalition_id: str = Field(default_factory=lambda: str(uuid4()))
    threat_id: str
    segments: list[Segment] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)


class CoalitionRecord(BaseModel):
    coalition_id: str
    members: list[str] = Field(default_factory=list)
    lead_rca: str
    threat_id: str
