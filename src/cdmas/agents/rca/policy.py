"""Proportional response selection (SDD §4.1, Figure 6).

Pick the least-disruptive action that still neutralizes the threat. The right action
depends on BOTH severity and attack type: a volumetric attack (DDoS) is throttled to
preserve availability — quarantining a public segment would itself cause an outage —
whereas a host compromise (lateral movement, ransomware, novel) is escalated to
quarantine when severe enough, which requires a coalition vote.
"""

from __future__ import annotations

from dataclasses import dataclass

from cdmas.common.models.enums import AttackType, ResponseType

_DISRUPTION: dict[ResponseType, float] = {
    ResponseType.MONITOR: 0.0,
    ResponseType.THROTTLE: 0.2,
    ResponseType.BLOCK: 0.5,
    ResponseType.REDEPLOY: 0.6,
    ResponseType.QUARANTINE: 0.9,
}

_VOLUMETRIC = {AttackType.DDOS, AttackType.VOLUME_SPIKE}
_CONTAINMENT = {AttackType.LATERAL, AttackType.RANSOMWARE, AttackType.NOVEL, AttackType.ZERO_DAY}


@dataclass(frozen=True)
class ResponseAction:
    type: ResponseType
    disruption_score: float


def _action(rtype: ResponseType) -> ResponseAction:
    return ResponseAction(rtype, _DISRUPTION[rtype])


def select_proportional_action(severity: float, attack_type: AttackType) -> ResponseAction:
    if severity < 0.3:
        return _action(ResponseType.MONITOR)
    if attack_type in _VOLUMETRIC:
        # Throttle to preserve availability; block only an extreme flood.
        return _action(ResponseType.BLOCK if severity >= 0.95 else ResponseType.THROTTLE)
    if attack_type is AttackType.PORT_SCAN:
        return _action(ResponseType.BLOCK)
    if attack_type in _CONTAINMENT:
        if severity >= 0.85:
            return _action(ResponseType.QUARANTINE)  # contain the spread (requires a vote)
        if severity >= 0.6:
            return _action(ResponseType.REDEPLOY)
        return _action(ResponseType.BLOCK)
    return _action(ResponseType.THROTTLE if severity < 0.6 else ResponseType.BLOCK)


def proportionality_score(action: ResponseAction) -> float:
    """Higher = more proportional (less disruptive). Always >= 0.7 for the catalog."""
    return round(1.0 - 0.3 * action.disruption_score, 3)
