from cdmas.agents.tma.agent import TrafficMonitorAgent
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator


async def test_tma_detects_ddos_after_warmup():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=0)
    bus = InMemoryBus()
    observer = bus.subscribe(Topic.ALERTS, "OBSERVER")
    tma = TrafficMonitorAgent("TMA:seg1", "public-facing", bus, sim, clock=clk)
    tma.setup()

    # Warm up the baseline on normal traffic.
    for _ in range(10):
        sim.tick()
        await tma.step()
        clk.advance(10)
    assert await observer.get(timeout=0.01) is None  # nothing anomalous yet

    # Inject a DDoS flood.
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    sim.tick()
    await tma.step()
    clk.advance(10)

    msg = await observer.get(timeout=0.05)
    assert msg is not None
    assert msg.content["alert"]["deviation_score"] > 2.0
    assert "features" in msg.content


async def test_tma_alert_latency_under_100ms():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=1)
    bus = InMemoryBus()
    tma = TrafficMonitorAgent("TMA:seg1", "public-facing", bus, sim, clock=clk)
    tma.setup()
    for _ in range(8):
        sim.tick()
        await tma.step()
        clk.advance(10)
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=3.0))
    sim.tick()
    await tma.step()

    alerts = [e for e in tma.sink.events if e.event_type is EventType.ALERT_PUBLISHED]
    assert alerts
    assert alerts[-1].latency_ms is not None and alerts[-1].latency_ms < 100
