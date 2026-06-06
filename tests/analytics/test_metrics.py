from cdmas.analytics.metrics import compute_metrics
from cdmas.analytics.social_welfare import SW_THRESHOLD, WEIGHTS, social_welfare
from cdmas.analytics.utilities import RawMetrics, compute_utilities
from cdmas.common.logging.event_log import EventLog, EventType
from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackSpec, GroundTruth


def _ev(
    event_type: EventType,
    segment: str | None,
    *,
    latency: int | None = None,
    wall: float = 100.0,
    **payload,
) -> EventLog:
    return EventLog(
        lamport_ts=1,
        wall_ms=wall,
        event_type=event_type,
        agent_id="x",
        agent_type="x",
        segment=segment,
        payload=payload,
        latency_ms=latency,
    )


def _successful_events() -> list[EventLog]:
    return [
        _ev(EventType.ALERT_PUBLISHED, "public-facing", signal="alert", latency=20),
        _ev(
            EventType.THREAT_CLASSIFIED,
            "public-facing",
            signal="classify",
            reported=True,
            threat_id="t1",
            classification="CONFIRMED_THREAT",
            latency=40,
        ),
        _ev(
            EventType.ACTION_EXECUTED,
            "public-facing",
            signal="response",
            action="THROTTLE",
            proportionality_score=0.94,
            severity=0.9,
            latency=40,
            wall=400.0,
        ),
        _ev(EventType.ACTION_EXECUTED, "public-facing", signal="threat_model_update", latency=30),
        _ev(EventType.RESOURCE_ALLOCATED, None, signal="overhead", overhead=0.2),
    ]


def test_successful_run_hits_targets():
    gt = GroundTruth(attacks=[AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING)])
    m = compute_metrics(_successful_events(), gt, segment_count=1, total_time_ms=60_000)
    assert m.dr == 1.0
    assert m.fpr == 0.0
    assert m.mttr_alert_ms == 20
    assert m.mttr_response_ms == 40
    assert m.availability > 0.99
    assert m.resource_overhead < 0.40
    assert m.social_welfare >= SW_THRESHOLD
    assert m.attacker_utility < 0.2


def test_undetected_attack_tanks_social_welfare():
    gt = GroundTruth(attacks=[AttackSpec(type=AttackType.DDOS, segment=Segment.SERVER)])
    # An attack with no detection/response logged.
    events = [_ev(EventType.RESOURCE_ALLOCATED, None, signal="overhead", overhead=0.2)]
    m = compute_metrics(events, gt, segment_count=1, total_time_ms=60_000)
    assert m.dr == 0.0
    assert m.social_welfare < SW_THRESHOLD


def test_weights_sum_to_one_and_sw_matches_formula():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    utils = {"TMA": 1.0, "ACA": 1.0, "RCA": 1.0, "RAA": 1.0, "TIA": 1.0}
    assert social_welfare(utils) == 1.0


def test_compute_utilities_bounded():
    raw = RawMetrics(
        dr=1.0,
        fpr=0.0,
        accuracy=1.0,
        mttr_alert_ms=0.0,
        mttr_response_ms=0.0,
        mttr_coalition_ms=0.0,
        availability=1.0,
        resource_overhead=0.0,
        proportionality=1.0,
        resource_efficiency=1.0,
        intelligence_coverage=1.0,
        correlation_accuracy=1.0,
    )
    utils = compute_utilities(raw)
    assert all(0.0 <= v <= 1.0 for v in utils.values())
    assert utils["ACA"] == 1.0
