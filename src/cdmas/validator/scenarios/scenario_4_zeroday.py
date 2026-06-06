"""Scenario 4 - Zero-Day / Novel Attack Detection (SRS §8.4)."""

from __future__ import annotations

from cdmas.agents.attackers.zero_day import ZeroDayEmulator
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=[Segment.PUBLIC_FACING], seed=4)
    h.add_attacker(
        ZeroDayEmulator(
            "ATK:zd", "public-facing", h.bus, h.sim, h.sink, clock=h.clock, intensity=2.0
        )
    )
    await h.warmup(30)
    await h.run(40)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    by_fr = {c.fr_id: c for c in r.constraints}
    return {
        "novel_detected": by_fr["FR-26"].status == "PASS",
        "FPR<10%": m.fpr < 0.10,
        "SW>=0.80": m.social_welfare >= 0.80,
    }
