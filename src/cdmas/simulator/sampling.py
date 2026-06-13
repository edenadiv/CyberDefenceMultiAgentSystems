"""Size-budgeted, representative packet sampling for the dashboard replay (SDD dashboard ext.).

The simulator emits tens of thousands of packets per scenario. Dumping them all would bloat
the offline replay bundle and stutter the war-room. Instead the sampler keeps a tiny,
deterministic, visually-representative subset — real attacker IPs/ports, a few benign flows —
capped by a hard budget. Packets are NOT events: they live in a sibling ``packets`` array and
never reach the FR constraint checker or metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cdmas.common.models.enums import Segment
from cdmas.simulator.packet import Packet

# Budget — keep the replay small and the war-room legible.
MAX_PER_FLOW = 6  # distinct representatives kept per (segment, kind) flow
MAX_TOTAL = 80  # hard cap on sampled packets per scenario
BENIGN_QUOTA = 8  # a few normal flows so the audience sees green traffic too

# Visual kinds shown in the dashboard.
KINDS = ("benign", "ddos", "port_scan", "lateral", "zero_day")


@dataclass(frozen=True)
class SampledPacket:
    src_ip: str
    dst_ip: str
    port: int
    protocol: str
    pkt_size: int
    freq: float
    ts_ms: float
    kind: str
    segment: str
    alert_ms: float | None = None  # filled in by the harness via alert-correlation


def classify_kind(p: Packet) -> str:
    """Map a packet to a visual kind from its (real) signature.

    Signatures come straight from ``AttackInjector``: DDoS/volume spoof ``203.0.x.x``,
    port-scan from ``198.51.100.7``, zero-day from ``192.0.2.66``, lateral movement over
    SMB/445. Everything else is benign baseline traffic.
    """
    if p.src_ip.startswith("203.0."):
        return "ddos"
    if p.src_ip == "198.51.100.7":
        return "port_scan"
    if p.src_ip == "192.0.2.66":
        return "zero_day"
    if p.port == 445:
        return "lateral"
    return "benign"


def _flow_key(p: Packet, kind: str) -> Any:
    """What makes a packet a *distinct representative* within its flow."""
    if kind == "ddos":
        return p.src_ip  # distinct bots
    if kind == "port_scan":
        return p.port  # distinct scanned ports
    if kind == "lateral":
        return p.dst_ip  # distinct targets
    if kind == "zero_day":
        return p.ts_ms  # one pulse per tick
    return p.src_ip  # benign: distinct clients


class PacketSampler:
    """Capped reservoir keyed by (segment, kind); keeps the first distinct representatives."""

    def __init__(self) -> None:
        self._flows: dict[tuple[str, str], dict[Any, SampledPacket]] = {}

    def observe(
        self,
        segment: Segment | str,
        now_ms: float,
        benign: list[Packet],
        malicious: list[Packet],
    ) -> None:
        seg = segment.value if isinstance(segment, Segment) else str(segment)
        for p in malicious:
            self._add(seg, classify_kind(p), p, now_ms)
        for p in benign:
            self._add(seg, "benign", p, now_ms)

    def _add(self, seg: str, kind: str, p: Packet, now_ms: float) -> None:
        if self._total() >= MAX_TOTAL:
            return
        bucket = self._flows.setdefault((seg, kind), {})
        per_flow = BENIGN_QUOTA if kind == "benign" else MAX_PER_FLOW
        if len(bucket) >= per_flow:
            return
        key = _flow_key(p, kind)
        if key in bucket:
            return
        bucket[key] = SampledPacket(
            src_ip=p.src_ip,
            dst_ip=p.dst_ip,
            port=p.port,
            protocol=p.protocol,
            pkt_size=p.pkt_size,
            freq=round(p.freq, 1),
            ts_ms=round(now_ms, 1),
            kind=kind,
            segment=seg,
        )

    def _total(self) -> int:
        return sum(len(bucket) for bucket in self._flows.values())

    def export(self) -> list[dict[str, Any]]:
        rows = [sp for bucket in self._flows.values() for sp in bucket.values()]
        rows.sort(key=lambda sp: (sp.ts_ms, sp.segment, sp.kind, str(sp.src_ip), sp.port))
        return [asdict(sp) for sp in rows]


def correlate_alert_ms(
    packets: list[dict[str, Any]], alerts_by_segment: dict[str, list[float]]
) -> None:
    """Stamp each packet with the alert it triggered: the nearest ALERT_PUBLISHED at/after
    the packet's ts_ms on the same segment. Lets the dashboard land a sprite's *arrival* at
    the moment of detection. Mutates the dicts in place; alert_ms stays None when no later
    alert exists on that segment.
    """
    for p in packets:
        times = alerts_by_segment.get(p["segment"])
        if not times:
            continue
        following = [a for a in times if a >= p["ts_ms"]]
        if following:
            p["alert_ms"] = min(following)
