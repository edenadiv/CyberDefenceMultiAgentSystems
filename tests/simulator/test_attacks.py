from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.topology import NetworkTopology


def test_ddos_raises_volume_and_randomizes_ips():
    inj = AttackInjector(seed=1)
    inj.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    pkts = inj.overlay(Segment.PUBLIC_FACING, now_ms=0)
    assert len(pkts) >= 20
    assert len({p.src_ip for p in pkts}) > 10  # randomized botnet IPs
    assert max(p.freq for p in pkts) > 1000  # high volume


def test_port_scan_touches_distinct_ports_in_varied_order():
    inj = AttackInjector(seed=1)
    inj.inject(AttackSpec(type=AttackType.PORT_SCAN, segment=Segment.SERVER))
    ports = [p.port for p in inj.overlay(Segment.SERVER, now_ms=0)]
    assert len(set(ports)) == len(ports)  # distinct ports
    assert ports != sorted(ports)  # pseudo-random order


def test_lateral_only_to_adjacent_segments():
    topo = NetworkTopology()
    inj = AttackInjector(seed=1, topology=topo)
    inj.inject(AttackSpec(type=AttackType.LATERAL, segment=Segment.INTERNAL))
    pkts = inj.overlay(Segment.INTERNAL, now_ms=0)
    neighbor_idx = {list(Segment).index(n) for n in topo.neighbors(Segment.INTERNAL)}
    assert pkts
    for p in pkts:
        assert int(p.dst_ip.split(".")[1]) in neighbor_idx


def test_zero_day_is_out_of_distribution():
    inj = AttackInjector(seed=1)
    inj.inject(AttackSpec(type=AttackType.ZERO_DAY, segment=Segment.PUBLIC_FACING))
    pkts = inj.overlay(Segment.PUBLIC_FACING, now_ms=0)
    assert pkts and pkts[0].pkt_size >= 9000 and pkts[0].port == 31337


def test_active_window_and_ground_truth():
    inj = AttackInjector(seed=1)
    spec = AttackSpec(type=AttackType.DDOS, segment=Segment.SERVER, start_ms=100, duration_ms=50)
    inj.inject(spec)
    assert inj.active(now_ms=50) == []
    assert inj.active(now_ms=120) == [spec]
    assert inj.active(now_ms=200) == []
    gt = inj.ground_truth()
    assert gt.is_attack(Segment.SERVER, 120) is True
    assert gt.is_attack(Segment.SERVER, 50) is False
    assert gt.is_attack(Segment.INTERNAL, 120) is False


def test_prune_expired_drops_only_elapsed_bounded_attacks():
    inj = AttackInjector(seed=0, topology=NetworkTopology())
    inj.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, duration_ms=100))
    inj.inject(
        AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, duration_ms=0)
    )  # unbounded
    inj.inject(
        AttackSpec(
            type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, start_ms=500, duration_ms=100
        )
    )  # future
    assert inj.prune_expired(now_ms=300) == 1  # only the first (window elapsed) is dropped
    assert inj.prune_expired(now_ms=300) == 0  # idempotent
    # the unbounded attack and the not-yet-started one survive
    assert len(inj.ground_truth().attacks) == 2
