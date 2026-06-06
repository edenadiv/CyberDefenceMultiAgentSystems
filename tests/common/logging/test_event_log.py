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
