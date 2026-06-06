"""Threat report published by an Anomaly Classifier Agent (SDD §3.2.2)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import AttackType, Classification, Segment


class ThreatReport(BaseModel):
    threat_id: str = Field(default_factory=lambda: str(uuid4()))
    alert_id: str
    classification: Classification
    attack_type: AttackType
    severity: float = Field(ge=0.0, le=1.0)
    segment: Segment
    confidence: float = Field(ge=0.0, le=1.0)
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
