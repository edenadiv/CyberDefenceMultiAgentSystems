"""Scenario report assembly (SDD §7.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cdmas.analytics.metrics import compute_raw
from cdmas.analytics.social_welfare import SW_THRESHOLD
from cdmas.analytics.utilities import compute_utilities
from cdmas.common.logging.event_log import EventLog
from cdmas.common.models.metrics import MetricsSnapshot
from cdmas.simulator.attacks import GroundTruth


class ScenarioReport(BaseModel):
    scenario: str
    metrics: MetricsSnapshot
    utilities: dict[str, float] = Field(default_factory=dict)
    social_welfare_pass: bool
    criteria: dict[str, bool] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.social_welfare_pass and all(self.criteria.values())


def build_report(
    scenario: str,
    events: list[EventLog],
    ground_truth: GroundTruth,
    metrics: MetricsSnapshot,
    criteria: dict[str, bool],
    *,
    segment_count: int | None = None,
    total_time_ms: float | None = None,
) -> ScenarioReport:
    raw = compute_raw(
        events, ground_truth, segment_count=segment_count, total_time_ms=total_time_ms
    )
    utilities = compute_utilities(raw)
    return ScenarioReport(
        scenario=scenario,
        metrics=metrics,
        utilities=utilities,
        # Single source of truth: the Social Welfare already computed in `metrics`.
        social_welfare_pass=metrics.social_welfare >= SW_THRESHOLD,
        criteria=criteria,
    )
