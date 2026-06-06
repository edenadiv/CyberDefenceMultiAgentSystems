from cdmas.common.logging.event_log import DecisionTrace, EventLog, EventType
from cdmas.validator.constraints import ALL_CONSTRAINTS, CheckContext, check_all, covered_frs


def _ev(et, *, latency=None, signal=None, wall=0.0, trace=False, **payload):
    return EventLog(
        lamport_ts=1,
        wall_ms=wall,
        event_type=et,
        agent_id="x",
        agent_type="x",
        segment="public-facing",
        payload={"signal": signal, **payload},
        latency_ms=latency,
        decision_trace=DecisionTrace(inputs={}, plan_selected="p", reasoning="r", action="a")
        if trace
        else None,
    )


def test_all_34_frs_present():
    assert covered_frs() == {f"FR-{n:02d}" for n in range(1, 35)}
    assert len(ALL_CONSTRAINTS) == 34


def test_check_all_returns_one_result_per_fr():
    results = check_all(CheckContext(events=[], metrics=None))
    assert len(results) == 34
    # With no events/metrics every checker is NA, never FAIL.
    assert all(r.status == "NA" for r in results)


def test_latency_pass_and_fail():
    fast = CheckContext([_ev(EventType.ALERT_PUBLISHED, latency=50, deviation_score=3.0)], None)
    slow = CheckContext([_ev(EventType.ALERT_PUBLISHED, latency=150, deviation_score=3.0)], None)
    by_fr = {r.fr_id: r for r in check_all(fast)}
    assert by_fr["FR-03"].status == "PASS"
    by_fr_slow = {r.fr_id: r for r in check_all(slow)}
    assert by_fr_slow["FR-03"].status == "FAIL"


def test_quarantine_without_vote_fails_fr11():
    ctx = CheckContext(
        [
            _ev(
                EventType.ACTION_EXECUTED,
                signal="response",
                action="QUARANTINE",
                vote_id="v1",
                trace=True,
            )
        ],
        None,
    )
    by_fr = {r.fr_id: r for r in check_all(ctx)}
    assert by_fr["FR-11"].status == "FAIL"  # no majority vote recorded
