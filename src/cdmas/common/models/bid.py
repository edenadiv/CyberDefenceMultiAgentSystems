"""Resource bidding payloads for the sealed-bid auction (SDD §3.2.3)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import ResourceType


class ResourceBid(BaseModel):
    bid_id: str = Field(default_factory=lambda: str(uuid4()))
    bidder_id: str
    resource_type: ResourceType
    quantity: int = 1
    bid_value: float = Field(ge=0.0, le=1.0)  # = threat severity (FR auction rule)
    justification_threat_id: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuctionResult(BaseModel):
    auction_id: str = Field(default_factory=lambda: str(uuid4()))
    granted: dict[str, int] = Field(default_factory=dict)  # bidder_id -> quantity
    denied: list[str] = Field(default_factory=list)
    closed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
