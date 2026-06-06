"""Alert payload published by a Traffic Monitor Agent (SDD §3.2.1)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from cdmas.common.models.enums import AttackType, Segment


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Alert(BaseModel):
    alert_id: str = Field(default_factory=_uuid)
    segment: Segment
    anomaly_type: AttackType
    deviation_score: float
    src_ips: list[str] = Field(default_factory=list)
    dst_port: int
    traffic_volume: float
    baseline_mean: float
    baseline_std: float
    detected_at: datetime = Field(default_factory=_now)
