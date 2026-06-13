import pytest

from cdmas.analytics.metrics import compute_metrics
from cdmas.analytics.reports import build_report
from cdmas.common.logging.event_log import EventLog, EventType
from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackSpec, GroundTruth


def _events() -> list[EventLog]:
    return [
        EventLog(
            lamport_ts=1,
            wall_ms=10.0,
            event_type=EventType.THREAT_CLASSIFIED,
            agent_id="ACA:public-facing",
            agent_type="ACA",
            segment="public-facing",
            payload={"signal": "classify", "reported": True, "threat_id": "t1"},
            latency_ms=40,
        ),
        EventLog(
            lamport_ts=2,
            wall_ms=20.0,
            event_type=EventType.ACTION_EXECUTED,
            agent_id="RCA:public-facing",
            agent_type="RCA",
            segment="public-facing",
            payload={"signal": "response", "action": "THROTTLE", "proportionality_score": 0.94},
            latency_ms=40,
        ),
    ]


def test_build_report_assembles_metrics_and_verdict():
    gt = GroundTruth(attacks=[AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING)])
    metrics = compute_metrics(_events(), gt, segment_count=1, total_time_ms=60_000)
    report = build_report(
        "Scenario 1",
        _events(),
        gt,
        metrics,
        criteria={"DR>90%": metrics.dr > 0.9, "MTTR<1000": metrics.mttr_response_ms < 1000},
        segment_count=1,
        total_time_ms=60_000,
    )
    assert report.scenario == "Scenario 1"
    assert set(report.utilities) == {"TMA", "ACA", "RCA", "RAA", "TIA"}
    assert report.passed is True


@pytest.mark.integration
async def test_postgres_sink_roundtrip():
    """Requires the cdmas PostgreSQL (docker compose up postgres); skipped if unavailable."""
    from asyncpg.exceptions import PostgresError
    from sqlalchemy.exc import InterfaceError, OperationalError

    from cdmas.common.config import get_settings
    from cdmas.common.logging.postgres_sink import PostgresSink

    sink = PostgresSink(get_settings().db_url)
    try:
        await sink.create_schema()
    except (OSError, OperationalError, InterfaceError, PostgresError) as e:
        pytest.skip(f"PostgreSQL (cdmas role/db) not available: {e}")
    try:
        await sink.write(_events()[0])
    finally:
        await sink.close()
