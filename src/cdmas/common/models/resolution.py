"""Resolution notice broadcast when a threat is neutralized (SDD §3.3.1)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import Segment


class ResolutionNotice(BaseModel):
    resolution_id: str = Field(default_factory=lambda: str(uuid4()))
    threat_id: str
    segment: Segment
    outcome: str
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
