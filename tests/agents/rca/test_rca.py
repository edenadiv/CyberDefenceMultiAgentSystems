from cdmas.agents.rca.agent import ResponseCoordinatorAgent
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.engine import InProcessSimulator


def _threat(severity: float, seg: str = "public-facing") -> dict:
    return {
        "threat_id": "t1",
        "alert_id": "a1",
        "classification": "CONFIRMED_THREAT",
        "attack_type": "DDOS",
        "severity": severity,
        "segment": seg,
        "confidence": 0.9,
    }


async def test_rca_responds_to_confirmed_threat():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=0)
    bus = InMemoryBus()
    resolutions = bus.subscribe(Topic.RESOLUTION, "OBSERVER")
    rca = ResponseCoordinatorAgent("RCA:seg1", "public-facing", bus, sim, clock=clk)
    rca.setup()

    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="ACA:seg1",
            receiver="BROADCAST",
            topic=Topic.THREAT_REPORTS,
            seq=1,
            content={"threat": _threat(0.9), "ts_ms": 0.0},
        )
    )
    clk.advance(20)
    await rca.step()

    actions = [
        e
        for e in rca.sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("signal") == "response"
    ]
    assert actions
    assert actions[-1].payload["action"] == "THROTTLE"  # least disruptive effective
    assert actions[-1].latency_ms is not None and actions[-1].latency_ms < 500
    assert actions[-1].payload["proportionality_score"] >= 0.7

    res = await resolutions.get(timeout=0.05)
    assert res is not None and "resolution" in res.content


async def test_rca_ignores_low_severity():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=0)
    bus = InMemoryBus()
    rca = ResponseCoordinatorAgent("RCA:seg1", "public-facing", bus, sim, clock=clk)
    rca.setup()
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="ACA:seg1",
            receiver="BROADCAST",
            topic=Topic.THREAT_REPORTS,
            seq=1,
            content={"threat": {**_threat(0.5), "classification": "SUSPICIOUS"}, "ts_ms": 0.0},
        )
    )
    await rca.step()
    assert not [e for e in rca.sink.events if e.payload.get("signal") == "response"]
