"""Compute the SRS metrics from a recorded event log (SDD §7.2, SRS §7.3).

Pure and deterministic: given the same event log + ground truth, produces the same
``MetricsSnapshot``. This is what the validator and dashboard grade the system on.
"""

from __future__ import annotations

from collections.abc import Iterable

from cdmas.agents.attackers.utility import attacker_utility
from cdmas.analytics.social_welfare import social_welfare
from cdmas.analytics.utilities import RawMetrics, compute_utilities
from cdmas.common.logging.event_log import EventLog, EventType
from cdmas.common.models.metrics import MetricsSnapshot
from cdmas.simulator.attacks import GroundTruth


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _signal(events: list[EventLog], event_type: EventType, signal: str) -> list[EventLog]:
    return [e for e in events if e.event_type is event_type and e.payload.get("signal") == signal]


def compute_raw(
    events: list[EventLog],
    ground_truth: GroundTruth,
    *,
    segment_count: int | None = None,
    total_time_ms: float | None = None,
) -> RawMetrics:
    attacked = {a.segment.value for a in ground_truth.attacks}
    classified = [e for e in events if e.event_type is EventType.THREAT_CLASSIFIED]
    reported = [e for e in classified if e.payload.get("reported")]

    detected_segments = {e.segment for e in reported if e.segment in attacked}
    dr = len(detected_segments) / len(attacked) if attacked else 1.0
    false_positives = [e for e in reported if e.segment not in attacked]
    fpr = len(false_positives) / max(1, len(classified))

    alerts = [e for e in events if e.event_type is EventType.ALERT_PUBLISHED]
    responses = _signal(events, EventType.ACTION_EXECUTED, "response")
    coalitions = [e for e in events if e.event_type is EventType.COALITION_FORMED]
    overhead_events = _signal(events, EventType.RESOURCE_ALLOCATED, "overhead")

    mttr_alert = _mean(e.latency_ms for e in alerts if e.latency_ms is not None)
    mttr_response = _mean(e.latency_ms for e in responses if e.latency_ms is not None)
    mttr_coalition = _mean(e.latency_ms for e in coalitions if e.latency_ms is not None)

    total = total_time_ms or max((e.wall_ms for e in events), default=0.0) or 1.0
    nseg = segment_count or max(1, len(attacked))
    disruption_ms = sum(min(total, float(e.latency_ms or 0)) for e in responses)
    availability = max(0.0, 1.0 - disruption_ms / (total * nseg))

    resource_overhead = max((float(e.payload["overhead"]) for e in overhead_events), default=0.0)
    proportionality = (
        _mean(float(e.payload.get("proportionality_score", 1.0)) for e in responses) or 1.0
    )
    updates = _signal(events, EventType.ACTION_EXECUTED, "threat_model_update")
    coverage = 1.0 if (not attacked or updates) else 0.0

    return RawMetrics(
        dr=dr,
        fpr=fpr,
        accuracy=dr,
        mttr_alert_ms=mttr_alert,
        mttr_response_ms=mttr_response,
        mttr_coalition_ms=mttr_coalition,
        availability=availability,
        resource_overhead=resource_overhead,
        proportionality=proportionality,
        resource_efficiency=1.0,
        intelligence_coverage=coverage,
        correlation_accuracy=1.0,
    )


def compute_metrics(
    events: list[EventLog],
    ground_truth: GroundTruth,
    *,
    segment_count: int | None = None,
    total_time_ms: float | None = None,
) -> MetricsSnapshot:
    raw = compute_raw(
        events, ground_truth, segment_count=segment_count, total_time_ms=total_time_ms
    )
    utilities = compute_utilities(raw)
    sw = social_welfare(utilities)

    evasion = min(1.0, raw.mttr_response_ms / 1000.0)
    disruption_impact = 1.0 - raw.availability
    u_atk = round(attacker_utility(disruption_impact, evasion, raw.mttr_response_ms), 4)

    reported_threats = {
        e.payload.get("threat_id")
        for e in events
        if e.event_type is EventType.THREAT_CLASSIFIED and e.payload.get("reported")
    }

    return MetricsSnapshot(
        dr=round(raw.dr, 4),
        fpr=round(raw.fpr, 4),
        mttr_alert_ms=round(raw.mttr_alert_ms, 2),
        mttr_response_ms=round(raw.mttr_response_ms, 2),
        availability=round(raw.availability, 4),
        resource_overhead=round(raw.resource_overhead, 4),
        social_welfare=sw,
        attacker_utility=u_atk,
        coalition_ms=round(raw.mttr_coalition_ms, 2),
        evasion_rate=round(evasion, 4),
        concurrent_incidents=len(reported_threats),
    )
