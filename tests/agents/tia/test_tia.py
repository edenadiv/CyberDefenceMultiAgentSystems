from cdmas.agents.tia.agent import ThreatIntelligenceAgent
from cdmas.agents.tia.threat_map import GlobalThreatMap, ThreatEntry
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative, Segment
from cdmas.common.timing.clock import ManualClock


def test_threat_map_active_segments_and_priority():
    m = GlobalThreatMap()
    m.add(ThreatEntry("t1", Segment.SERVER, 0.9, 100.0, "DDOS"))
    m.add(ThreatEntry("t2", Segment.INTERNAL, 0.5, 200.0, "LATERAL"))
    assert m.active_segments(now_ms=300.0) == {Segment.SERVER, Segment.INTERNAL}
    assert m.active_segments(now_ms=5000.0) == set()  # outside window
    assert [e.threat_id for e in m.priority_list()] == ["t1", "t2"]


def _report(seg: str, sev: float) -> ACLMessage:
    return ACLMessage(
        performative=Performative.INFORM,
        sender=f"ACA:{seg}",
        receiver="BROADCAST",
        topic=Topic.THREAT_REPORTS,
        content={
            "threat": {
                "threat_id": f"t-{seg}",
                "segment": seg,
                "severity": sev,
                "attack_type": "DDOS",
            },
            "ts_ms": 0.0,
        },
    )


async def test_tia_detects_multi_segment_correlation():
    clk = ManualClock()
    bus = InMemoryBus()
    tia = ThreatIntelligenceAgent("TIA:global", None, bus, clock=clk)
    tia.setup()

    await bus.publish(_report("public-facing", 0.9))
    await bus.publish(_report("internal", 0.8))
    await tia.step()

    correlations = [
        e
        for e in tia.sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("signal") == "correlation"
    ]
    assert correlations
    assert set(correlations[-1].payload["segments"]) == {"public-facing", "internal"}
    assert correlations[-1].latency_ms is not None and correlations[-1].latency_ms < 1000


async def test_tia_publishes_priority_list():
    clk = ManualClock()
    bus = InMemoryBus()
    intel = bus.subscribe(Topic.THREAT_INTEL, "OBSERVER")
    tia = ThreatIntelligenceAgent("TIA:global", None, bus, clock=clk)
    tia.setup()
    await bus.publish(_report("server", 0.9))
    await tia.step()
    msg = await intel.get(timeout=0.05)
    assert msg is not None and msg.content["signal"] == "priority_list"
