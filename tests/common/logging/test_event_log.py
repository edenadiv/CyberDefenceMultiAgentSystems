from cdmas.common.logging.event_log import DecisionTrace, EventLog, EventType, InMemorySink


async def test_sink_records_events():
    sink = InMemorySink()
    e = EventLog(
        lamport_ts=7,
        wall_ms=1234.5,
        event_type=EventType.THREAT_CLASSIFIED,
        agent_id="ACA:seg1",
        agent_type="ACA",
        segment="public-facing",
        payload={"severity": 0.91},
        latency_ms=178,
        decision_trace=DecisionTrace(
            inputs={"alert_id": "a1"},
            plan_selected="classify_alert",
            reasoning="0.91 > threshold",
            action="PUBLISH_THREAT_REPORT",
        ),
    )
    await sink.write(e)
    assert len(sink.events) == 1
    assert sink.events[0].event_type is EventType.THREAT_CLASSIFIED
    assert sink.events[0].decision_trace.action == "PUBLISH_THREAT_REPORT"


def test_decision_trace_carries_structured_internals():
    trace = DecisionTrace(
        inputs={"alert_id": "a1"},
        plan_selected="classify",
        reasoning="confidence=0.97 novelty=0.02",
        action="PUBLISH_THREAT_REPORT",
        confidence=0.97,
        novelty=0.02,
        features=[1.0, 2.0, 3.0],
        feature_names=["volume", "mean_freq", "max_freq"],
        votes={"RCA:internal": "ACCEPT", "RCA:server": "REJECT"},
        vote_rationale={"RCA:internal": "severe, not overloaded"},
    )
    dumped = trace.model_dump(mode="json")
    assert dumped["confidence"] == 0.97
    assert dumped["novelty"] == 0.02
    assert dumped["feature_names"][0] == "volume"
    assert dumped["votes"]["RCA:internal"] == "ACCEPT"
    assert dumped["vote_rationale"]["RCA:internal"] == "severe, not overloaded"


def test_decision_trace_new_fields_default_none():
    # Back-compat: existing call sites that omit the new fields are unaffected.
    trace = DecisionTrace(plan_selected="respond", reasoning="x", action="BLOCK")
    assert trace.confidence is None
    assert trace.novelty is None
    assert trace.features is None
    assert trace.feature_names is None
    assert trace.votes is None
    assert trace.vote_rationale is None
