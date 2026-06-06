"""Scenario 1 - Single-Segment DDoS (SRS §8.1)."""

from __future__ import annotations

from cdmas.agents.attackers.ddos import DDoSAttacker
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=[Segment.PUBLIC_FACING], seed=1)
    h.add_attacker(
        DDoSAttacker(
            "ATK:ddos", "public-facing", h.bus, h.sim, h.sink, clock=h.clock, intensity=3.0
        )
    )
    await h.warmup(30)
    await h.run(40)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    return {
        "DR>90%": m.dr > 0.90,
        "MTTR_response<1000ms": m.mttr_response_ms < 1000,
        "availability>99%": m.availability > 0.99,
        "U_ATK<0.2": m.attacker_utility < 0.2,
        "SW>=0.80": m.social_welfare >= 0.80,
    }
