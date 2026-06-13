"""PacketSampler — the size-budgeted, representative packet capture for the dashboard.

The simulator generates tens of thousands of packets per scenario; the sampler keeps a tiny,
deterministic, visually-representative subset (real attacker IPs/ports) for the replay file.
"""

from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.packet import Packet
from cdmas.simulator.sampling import (
    BENIGN_QUOTA,
    MAX_PER_FLOW,
    MAX_TOTAL,
    PacketSampler,
    classify_kind,
    correlate_alert_ms,
)
from cdmas.simulator.topology import NetworkTopology
from cdmas.simulator.traffic import TrafficGenerator

SEG = Segment.PUBLIC_FACING


def _benign(n: int = 50) -> list[Packet]:
    return TrafficGenerator(seed=1).sample(SEG, n)


def _malicious(attack: AttackType, segment: Segment = SEG, intensity: float = 3.0) -> list[Packet]:
    inj = AttackInjector(seed=1, topology=NetworkTopology())
    inj.inject(AttackSpec(type=attack, segment=segment, intensity=intensity))
    return inj.overlay(segment, now_ms=0.0)


def test_classify_kind_matches_real_attack_signatures():
    assert classify_kind(_malicious(AttackType.DDOS)[0]) == "ddos"
    assert classify_kind(_malicious(AttackType.PORT_SCAN)[0]) == "port_scan"
    assert classify_kind(_malicious(AttackType.ZERO_DAY)[0]) == "zero_day"
    assert classify_kind(_benign()[0]) == "benign"
    lateral = _malicious(AttackType.LATERAL, segment=Segment.INTERNAL, intensity=2.0)
    assert lateral and classify_kind(lateral[0]) == "lateral"


def test_sampler_keeps_distinct_ddos_sources_within_per_flow_budget():
    sampler = PacketSampler()
    sampler.observe(SEG, 100.0, [], _malicious(AttackType.DDOS))  # 60 distinct bot IPs
    ddos = [p for p in sampler.export() if p["kind"] == "ddos"]
    assert len(ddos) == MAX_PER_FLOW
    assert len({p["src_ip"] for p in ddos}) == MAX_PER_FLOW  # all distinct
    assert all(p["src_ip"].startswith("203.0.") for p in ddos)  # real spoofed IPs
    assert all(p["segment"] == SEG.value for p in ddos)


def test_port_scan_keeps_distinct_ports_one_source():
    sampler = PacketSampler()
    sampler.observe(SEG, 100.0, [], _malicious(AttackType.PORT_SCAN))
    scan = [p for p in sampler.export() if p["kind"] == "port_scan"]
    assert len(scan) == MAX_PER_FLOW
    assert all(p["src_ip"] == "198.51.100.7" for p in scan)
    assert len({p["port"] for p in scan}) == MAX_PER_FLOW  # distinct scanned ports


def test_sampler_captures_a_few_benign_flows():
    sampler = PacketSampler()
    sampler.observe(SEG, 50.0, _benign(50), [])
    benign = [p for p in sampler.export() if p["kind"] == "benign"]
    assert 0 < len(benign) <= BENIGN_QUOTA


def test_sampler_respects_total_budget_across_ticks():
    sampler = PacketSampler()
    for now in range(0, 2000, 50):
        sampler.observe(SEG, float(now), _benign(50), _malicious(AttackType.DDOS))
    assert len(sampler.export()) <= MAX_TOTAL


def test_export_rows_are_json_safe_and_complete():
    import json

    sampler = PacketSampler()
    sampler.observe(SEG, 0.0, _benign(10), _malicious(AttackType.DDOS))
    rows = sampler.export()
    assert rows
    required = {
        "src_ip",
        "dst_ip",
        "port",
        "protocol",
        "pkt_size",
        "freq",
        "ts_ms",
        "kind",
        "segment",
        "alert_ms",
    }
    for r in rows:
        assert required <= set(r)
        assert r["alert_ms"] is None  # set later by harness alert-correlation
    json.dumps(rows)  # must not raise


def test_correlate_alert_ms_sets_nearest_following_alert():
    packets = [
        {"segment": "public-facing", "ts_ms": 100.0, "alert_ms": None},
        {"segment": "public-facing", "ts_ms": 250.0, "alert_ms": None},
        {"segment": "internal", "ts_ms": 100.0, "alert_ms": None},
    ]
    alerts_by_segment = {"public-facing": [200.0, 400.0]}
    correlate_alert_ms(packets, alerts_by_segment)
    assert packets[0]["alert_ms"] == 200.0  # the alert this burst triggered
    assert packets[1]["alert_ms"] == 400.0  # nearest alert at/after 250
    assert packets[2]["alert_ms"] is None  # no alerts recorded on 'internal'
