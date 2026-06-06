"""Per-agent utility functions (SRS §7.1).

The SRS formulas use 1/MTTR speed terms; we use the bounded form ``speed = 1 - MTTR/target``
clamped to [0, 1] so each utility lies in [0, 1] and Social Welfare is a [0, 1] score with
the SRS target of >= 0.80.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawMetrics:
    dr: float
    fpr: float
    accuracy: float
    mttr_alert_ms: float
    mttr_response_ms: float
    mttr_coalition_ms: float
    availability: float
    resource_overhead: float
    proportionality: float
    resource_efficiency: float
    intelligence_coverage: float
    correlation_accuracy: float


def speed(actual_ms: float, target_ms: float) -> float:
    if target_ms <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - actual_ms / target_ms))


def compute_utilities(m: RawMetrics) -> dict[str, float]:
    u_tma = m.dr * (1.0 - m.fpr) * speed(m.mttr_alert_ms, 100.0)
    u_aca = m.accuracy * (1.0 - m.fpr)
    u_rca = m.availability * speed(m.mttr_response_ms, 1000.0) * m.proportionality
    u_raa = m.resource_efficiency * (1.0 - m.resource_overhead)
    u_tia = m.intelligence_coverage * m.correlation_accuracy * speed(m.mttr_coalition_ms, 1000.0)
    return {
        "TMA": round(u_tma, 4),
        "ACA": round(u_aca, 4),
        "RCA": round(u_rca, 4),
        "RAA": round(u_raa, 4),
        "TIA": round(u_tia, 4),
    }
