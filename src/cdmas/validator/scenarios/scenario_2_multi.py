"""Scenario 2 - Multi-Segment Coordinated Attack (SRS §8.2)."""

from __future__ import annotations

from cdmas.agents.attackers.ddos import DDoSAttacker
from cdmas.agents.attackers.lateral import LateralMovementAgent
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=[Segment.PUBLIC_FACING, Segment.INTERNAL], seed=2)
    h.add_attacker(
        DDoSAttacker(
            "ATK:ddos",
            "public-facing",
            h.bus,
            h.sim,
            h.sink,
            clock=h.clock,
            intensity=3.0,
            mode="coordinated",
        )
    )
    h.add_attacker(
        LateralMovementAgent(
            "ATK:lat",
            "internal",
            h.bus,
            h.sim,
            h.sink,
            clock=h.clock,
            intensity=4.0,
            mode="coordinated",
        )
    )
    await h.warmup(30)
    await h.run(50)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    coalition_ms = m.coalition_ms if m.coalition_ms is not None else 1e9
    return {
        "coalition<1s": coalition_ms < 1000,
        "evasion<0.15": (m.evasion_rate or 0.0) < 0.15,
        "SW>=0.80": m.social_welfare >= 0.80,
    }
