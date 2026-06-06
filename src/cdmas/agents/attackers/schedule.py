"""Multi-attacker scheduling: independent by default, synchronized when coordinated.

FR-27: attackers act independently unless explicitly coordinated (FR-28), in which case a
shared schedule synchronizes their launch.
"""

from __future__ import annotations

from dataclasses import dataclass

from cdmas.simulator.attacks import AttackSpec


@dataclass
class ScheduledAttack:
    start_ms: float
    spec: AttackSpec


def build_schedule(
    specs: list[AttackSpec], *, coordinated: bool, stagger_ms: float = 500.0
) -> list[ScheduledAttack]:
    if coordinated:
        return [
            ScheduledAttack(0.0, spec.model_copy(update={"mode": "coordinated"})) for spec in specs
        ]
    return [
        ScheduledAttack(i * stagger_ms, spec.model_copy(update={"mode": "independent"}))
        for i, spec in enumerate(specs)
    ]
