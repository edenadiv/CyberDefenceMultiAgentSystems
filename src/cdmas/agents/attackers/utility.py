"""Attacker utility function (SRS §7.1.6).

U_ATK = disruption_impact x evasion_rate x (1 - 1/MTTR_response).
A low MTTR (fast defense) drives the attacker's utility toward zero.
"""

from __future__ import annotations


def attacker_utility(
    disruption_impact: float, evasion_rate: float, mttr_response_ms: float
) -> float:
    mttr = max(1.0, mttr_response_ms)  # clamp to avoid blow-up / negative values
    return disruption_impact * evasion_rate * (1.0 - 1.0 / mttr)
