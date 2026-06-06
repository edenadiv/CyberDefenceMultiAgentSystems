from cdmas.agents.raa.agent import ResourceAllocatorAgent
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.engine import InProcessSimulator


async def test_raa_monitors_overhead():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.SERVER], seed=0)
    bus = InMemoryBus()
    raa = ResourceAllocatorAgent("RAA:global", None, bus, sim, clock=clk)
    raa.setup()
    await raa.step()  # first monitor tick
    overhead = [
        e
        for e in raa.sink.events
        if e.event_type is EventType.RESOURCE_ALLOCATED and e.payload.get("signal") == "overhead"
    ]
    assert overhead
    assert overhead[-1].payload["status"] == "OK"  # idle sim under cap


async def test_raa_reclaims_on_resolution():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.SERVER], seed=0)
    bus = InMemoryBus()
    raa = ResourceAllocatorAgent("RAA:global", None, bus, sim, clock=clk)
    raa.setup()
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="RCA:seg1",
            receiver="BROADCAST",
            topic=Topic.RESOLUTION,
            seq=1,
            content={"resolution": {"threat_id": "t1"}, "ts_ms": 0.0},
        )
    )
    clk.advance(50)
    await raa.step()
    reclaims = [
        e
        for e in raa.sink.events
        if e.event_type is EventType.RESOURCE_ALLOCATED and e.payload.get("signal") == "reclaim"
    ]
    assert reclaims
    assert reclaims[-1].latency_ms is not None and reclaims[-1].latency_ms < 500
