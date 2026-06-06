"""Scenario 3 - Resource Contention Under Load (SRS §8.3).

Containment-class attacks across all four segments make the RCAs bid for the 3 available
quarantine slots; the RAA's sealed-bid auction allocates them to the highest severities.
"""

from __future__ import annotations

from cdmas.agents.attackers.lateral import LateralMovementAgent
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult

_SEGMENTS = [Segment.INTERNAL, Segment.SERVER, Segment.PUBLIC_FACING, Segment.SEC_MON]


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=_SEGMENTS, seed=3, quarantine_slots=3)
    for i, seg in enumerate(_SEGMENTS):
        h.add_attacker(
            LateralMovementAgent(
                f"ATK:lat{i}", seg.value, h.bus, h.sim, h.sink, clock=h.clock, intensity=4.0
            )
        )
    await h.warmup(30)
    await h.run(50)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    by_fr = {c.fr_id: c for c in r.constraints}
    return {
        "auction<300ms": by_fr["FR-19"].status in {"PASS", "NA"},
        "auction_top_severity": by_fr["FR-20"].status in {"PASS", "NA"},
        "overhead<=40%": m.resource_overhead <= 0.40,
        ">=5 incidents": m.concurrent_incidents >= 5,
        "SW>=0.80": m.social_welfare >= 0.80,
    }
