from cdmas.common.models.enums import AttackType, ResponseType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.models import ActionRequest
from cdmas.simulator.sampling import PacketSampler


def _sim(seg=Segment.PUBLIC_FACING) -> InProcessSimulator:
    return InProcessSimulator(clock=ManualClock(), segments=[seg], seed=0)


async def test_tick_generates_traffic():
    sim = _sim()
    sim.tick()
    pkts = await sim.get_packets(Segment.PUBLIC_FACING, 100)
    assert len(pkts) > 0


async def test_ddos_then_throttle_reduces_volume():
    sim = _sim()
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    sim.tick()
    before = sum(p.freq for p in await sim.get_packets(Segment.PUBLIC_FACING, 10_000))
    await sim.apply_action(ActionRequest(type=ResponseType.THROTTLE, segment=Segment.PUBLIC_FACING))
    sim.tick()
    after = sum(p.freq for p in await sim.get_packets(Segment.PUBLIC_FACING, 10_000))
    assert after < before  # throttle reduced effective volume
    state = await sim.get_state()
    assert state.segments[0].health == "UNDER_ATTACK"


async def test_quarantine_isolates_segment_traffic():
    sim = _sim(Segment.SERVER)
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.SERVER, intensity=1.0))
    await sim.apply_action(ActionRequest(type=ResponseType.QUARANTINE, segment=Segment.SERVER))
    sim.tick()
    # No malicious packets reach a quarantined segment (only baseline remains).
    pkts = await sim.get_packets(Segment.SERVER, 10_000)
    assert all(not p.src_ip.startswith("203.0.") for p in pkts)


async def test_tick_feeds_sampler_real_attack_packets():
    sampler = PacketSampler()
    sim = InProcessSimulator(
        clock=ManualClock(), segments=[Segment.PUBLIC_FACING], seed=0, sampler=sampler
    )
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=3.0))
    for _ in range(3):
        sim.tick()
    rows = sampler.export()
    ddos = [r for r in rows if r["kind"] == "ddos"]
    assert ddos and all(r["src_ip"].startswith("203.0.") for r in ddos)
    assert any(r["kind"] == "benign" for r in rows)  # some baseline captured too


async def test_topology_and_ground_truth():
    sim = _sim()
    view = await sim.get_topology()
    assert Segment.PUBLIC_FACING in view.segments
    sim.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING))
    assert sim.ground_truth().is_attack(Segment.PUBLIC_FACING, 0.0) is True
