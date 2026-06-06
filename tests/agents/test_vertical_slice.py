"""End-to-end vertical slice (milestone M2): DDoS -> detect -> classify -> respond."""

from cdmas.agents.factory import build_all
from cdmas.common.logging.event_log import EventType, InMemorySink
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator


async def test_single_segment_ddos_pipeline_under_mttr():
    clk = ManualClock()
    bus = InMemoryBus()
    sink = InMemorySink()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=0)
    agents = build_all([Segment.PUBLIC_FACING], bus, sim, sink, clk)
    for agent in agents:
        agent.setup()

    # Warm up baselines on normal traffic.
    for _ in range(12):
        sim.tick()
        for agent in agents:
            await agent.step()
        clk.advance(10)

    # Flood the segment.
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=3.0))
    for _ in range(6):
        sim.tick()
        for agent in agents:
            await agent.step()
        clk.advance(10)

    alerts = [e for e in sink.events if e.event_type is EventType.ALERT_PUBLISHED]
    classified = [e for e in sink.events if e.event_type is EventType.THREAT_CLASSIFIED]
    responses = [
        e
        for e in sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("signal") == "response"
    ]
    resolved = [e for e in sink.events if e.event_type is EventType.INCIDENT_RESOLVED]

    assert alerts, "TMA should have raised an alert"
    assert classified, "ACA should have classified the alert"
    assert responses, "RCA should have responded"
    assert resolved, "incident should have been resolved"

    # MTTR_response well under the 1000ms target.
    assert responses[-1].latency_ms is not None and responses[-1].latency_ms < 1000
    assert responses[-1].payload["action"] in {"THROTTLE", "BLOCK"}
