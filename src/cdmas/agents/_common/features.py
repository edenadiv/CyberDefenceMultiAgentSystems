"""Packet-stream feature extraction + synthetic labeled training data.

The same feature vector is used by the TMA (deviation) and the ACA (classification). The
training-set generator pairs the simulator's ``TrafficGenerator`` (normal) with the
``AttackInjector`` signatures (attacks) so the classifier's labels match what the injector
produces. Zero-day is deliberately held out of training (it is caught by novelty).
"""

from __future__ import annotations

import math
from collections import Counter

from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.packet import Packet
from cdmas.simulator.topology import NetworkTopology
from cdmas.simulator.traffic import TrafficGenerator

FEATURE_NAMES = [
    "volume",
    "mean_freq",
    "max_freq",
    "unique_src",
    "unique_dport",
    "port_entropy",
    "mean_size",
    "max_size",
    "udp_frac",
]
NUM_FEATURES = len(FEATURE_NAMES)

TRAIN_LABELS = ["NORMAL", "DDOS", "PORT_SCAN", "LATERAL"]

_LABEL_TO_ATTACK = {
    "DDOS": AttackType.DDOS,
    "PORT_SCAN": AttackType.PORT_SCAN,
    "LATERAL": AttackType.LATERAL,
}


def attack_type_for_label(label: str) -> AttackType:
    return _LABEL_TO_ATTACK.get(label, AttackType.NOVEL)


def _entropy(values: list[int]) -> float:
    if not values:
        return 0.0
    total = len(values)
    counts = Counter(values)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def extract_features(packets: list[Packet]) -> list[float]:
    if not packets:
        return [0.0] * NUM_FEATURES
    freqs = [p.freq for p in packets]
    sizes = [p.pkt_size for p in packets]
    ports = [p.port for p in packets]
    volume = float(sum(freqs))
    return [
        volume,
        volume / len(packets),
        float(max(freqs)),
        float(len({p.src_ip for p in packets})),
        float(len(set(ports))),
        _entropy(ports),
        float(sum(sizes) / len(sizes)),
        float(max(sizes)),
        float(sum(1 for p in packets if p.protocol == "UDP") / len(packets)),
    ]


def build_training_set(
    *,
    seed: int = 0,
    samples_per_class: int = 40,
    segment: Segment = Segment.PUBLIC_FACING,
    window: int = 50,
) -> tuple[list[list[float]], list[str]]:
    """Generate a labeled feature set for ACA cold-start (NORMAL + 3 attack types)."""
    topology = NetworkTopology()
    x: list[list[float]] = []
    y: list[str] = []
    for i in range(samples_per_class):
        gen = TrafficGenerator(seed=seed + i)
        base = gen.sample(segment, window)
        x.append(extract_features(base))
        y.append("NORMAL")

        intensity = 1.5 + (i % 6) * 0.5  # span 1.5..4.0 so strong floods stay in-cluster
        for offset, atk, label in (
            (1000, AttackType.DDOS, "DDOS"),
            (2000, AttackType.PORT_SCAN, "PORT_SCAN"),
            (3000, AttackType.LATERAL, "LATERAL"),
        ):
            inj = AttackInjector(seed=seed + offset + i, topology=topology)
            inj.inject(AttackSpec(type=atk, segment=segment, intensity=intensity))
            mal = inj.overlay(segment, now_ms=0.0)
            x.append(extract_features(base + mal))
            y.append(label)
    return x, y
