"""Attack injection: overlays malicious patterns onto the traffic stream (SDD §6.1.1)."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field

from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.packet import Packet
from cdmas.simulator.topology import NetworkTopology


class AttackSpec(BaseModel):
    type: AttackType
    segment: Segment
    intensity: float = 1.0
    duration_ms: int = 0  # <= 0 means "active from start_ms onward"
    start_ms: float = 0.0
    mode: str = "independent"  # | "coordinated"


class GroundTruth(BaseModel):
    """What was actually injected, used to score Detection Rate / FPR."""

    attacks: list[AttackSpec] = Field(default_factory=list)

    def is_attack(self, segment: Segment, ts_ms: float) -> bool:
        return any(_active(a, segment, ts_ms) for a in self.attacks)


def _active(spec: AttackSpec, segment: Segment | None, ts_ms: float) -> bool:
    if segment is not None and spec.segment != segment:
        return False
    if ts_ms < spec.start_ms:
        return False
    return spec.duration_ms <= 0 or ts_ms <= spec.start_ms + spec.duration_ms


class AttackInjector:
    def __init__(self, *, seed: int = 0, topology: NetworkTopology | None = None) -> None:
        self._rng = np.random.default_rng(seed)
        self._specs: list[AttackSpec] = []
        self._topology = topology

    def inject(self, spec: AttackSpec) -> None:
        self._specs.append(spec)

    def ground_truth(self) -> GroundTruth:
        return GroundTruth(attacks=list(self._specs))

    def active(self, now_ms: float) -> list[AttackSpec]:
        return [s for s in self._specs if _active(s, None, now_ms)]

    def prune_expired(self, now_ms: float) -> int:
        """Drop bounded attacks whose window has fully elapsed (keeps active + future).

        Used by the long-running live server to bound memory; the validator harness runs
        fixed-length scenarios and never calls it, so scoring is unaffected.
        """
        before = len(self._specs)
        self._specs = [
            s for s in self._specs if s.duration_ms <= 0 or now_ms <= s.start_ms + s.duration_ms
        ]
        return before - len(self._specs)

    def overlay(self, segment: Segment, now_ms: float) -> list[Packet]:
        """Malicious packets for `segment` from all attacks active at `now_ms`."""
        out: list[Packet] = []
        idx = list(Segment).index(segment)
        for spec in self.active(now_ms):
            if spec.segment != segment:
                continue
            out.extend(self._packets_for(spec, segment, idx, now_ms))
        return out

    def _packets_for(
        self, spec: AttackSpec, segment: Segment, idx: int, now_ms: float
    ) -> list[Packet]:
        if spec.type in (AttackType.DDOS, AttackType.VOLUME_SPIKE):
            count = max(20, int(spec.intensity * 20))
            pkts = []
            for _ in range(count):
                o1 = int(self._rng.integers(1, 255))
                o2 = int(self._rng.integers(1, 255))
                pkts.append(
                    Packet(
                        src_ip=f"203.0.{o1}.{o2}",
                        dst_ip=f"10.{idx}.0.1",
                        port=443,
                        pkt_size=512,
                        freq=5000.0 * spec.intensity,
                        ts_ms=now_ms,
                    )
                )
            return pkts
        if spec.type == AttackType.PORT_SCAN:
            ports = self._rng.permutation(np.arange(1, 1025))[:50]
            return [
                Packet(
                    src_ip="198.51.100.7",
                    dst_ip=f"10.{idx}.0.1",
                    port=int(p),
                    pkt_size=64,
                    freq=2.0,
                    ts_ms=now_ms,
                )
                for p in ports
            ]
        if spec.type == AttackType.LATERAL:
            neighbors = list(self._topology.neighbors(segment)) if self._topology else []
            if not neighbors:
                return []
            count = max(len(neighbors), int(spec.intensity * 15))
            pkts = []
            for i in range(count):
                nb = neighbors[i % len(neighbors)]
                nidx = list(Segment).index(nb)
                pkts.append(
                    Packet(
                        src_ip=f"10.{idx}.0.5",
                        dst_ip=f"10.{nidx}.0.9",
                        port=445,
                        pkt_size=256,
                        freq=300.0,
                        ts_ms=now_ms,
                    )
                )
            return pkts
        if spec.type in (AttackType.ZERO_DAY, AttackType.NOVEL):
            count = max(1, int(spec.intensity * 20))
            return [
                Packet(
                    src_ip="192.0.2.66",
                    dst_ip=f"10.{idx}.0.1",
                    port=31337,
                    protocol="UDP",
                    pkt_size=9000,
                    freq=4000.0,
                    ts_ms=now_ms,
                )
                for _ in range(count)
            ]
        return []
