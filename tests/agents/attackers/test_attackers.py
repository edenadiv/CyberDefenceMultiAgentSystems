from cdmas.agents.attackers.ddos import DDoSAttacker
from cdmas.agents.attackers.lateral import LateralMovementAgent
from cdmas.agents.attackers.port_scanner import PortScanner
from cdmas.agents.attackers.schedule import build_schedule
from cdmas.agents.attackers.utility import attacker_utility
from cdmas.agents.attackers.zero_day import ZeroDayEmulator
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator


def _action_event(agent):
    return next(
        e
        for e in agent.sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("signal") == "attack_action"
    )


async def test_ddos_injects_and_logs_randomized_ips():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.PUBLIC_FACING], seed=0)
    atk = DDoSAttacker("ATK:ddos", "public-facing", InMemoryBus(), sim, clock=clk, intensity=2.0)
    atk.setup()
    await atk.step()
    assert sim.ground_truth().is_attack(Segment.PUBLIC_FACING, 0.0)
    ev = _action_event(atk)
    assert len(set(ev.payload["src_ips"])) >= ev.payload["min_unique_ips"]


async def test_port_scanner_logs_varied_ports():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.SERVER], seed=0)
    atk = PortScanner("ATK:scan", "server", InMemoryBus(), sim, clock=clk, seed=3)
    atk.setup()
    await atk.step()
    ports = _action_event(atk).payload["ports"]
    assert len(set(ports)) == len(ports)
    assert ports != sorted(ports)


async def test_zero_day_and_lateral_inject():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.INTERNAL], seed=0)
    bus = InMemoryBus()
    zd = ZeroDayEmulator("ATK:zd", "internal", bus, sim, clock=clk)
    lat = LateralMovementAgent("ATK:lat", "internal", bus, sim, clock=clk)
    zd.setup()
    lat.setup()
    await zd.step()
    await lat.step()
    assert _action_event(zd).payload["attack_type"] == AttackType.ZERO_DAY.value
    assert _action_event(lat).payload["attack_type"] == AttackType.LATERAL.value


def test_attacker_utility_drops_with_fast_response():
    high = attacker_utility(1.0, 1.0, mttr_response_ms=100_000)
    low = attacker_utility(1.0, 1.0, mttr_response_ms=10)
    assert high > low
    assert attacker_utility(1.0, 1.0, 1.0) == 0.0  # MTTR floor -> zero utility


def test_schedule_coordinated_vs_independent():
    specs = [
        AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING),
        AttackSpec(type=AttackType.LATERAL, segment=Segment.INTERNAL),
    ]
    coord = build_schedule(specs, coordinated=True)
    assert {s.start_ms for s in coord} == {0.0}  # synchronized
    assert all(s.spec.mode == "coordinated" for s in coord)
    indep = build_schedule(specs, coordinated=False)
    assert indep[0].start_ms != indep[1].start_ms  # staggered
