"""Scenario 5 - Agent Failure & Resilience (SRS §8.5).

The Server-Zone ACA is terminated mid-run; the system reassigns its coverage within 2s and
keeps responding to an attack on a still-covered segment.
"""

from __future__ import annotations

from cdmas.agents.attackers.ddos import DDoSAttacker
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=[Segment.SERVER, Segment.PUBLIC_FACING], seed=5)
    h.add_attacker(
        DDoSAttacker(
            "ATK:ddos", "public-facing", h.bus, h.sim, h.sink, clock=h.clock, intensity=3.0
        )
    )
    await h.warmup(30)
    # Kill the Server-Zone ACA early; failover must reassign coverage within 2s.
    await h.run(60, fail_agent="ACA:server", fail_after_rounds=5)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    by_fr = {c.fr_id: c for c in r.constraints}
    return {
        "coverage_reassigned<2s": by_fr["FR-34"].status == "PASS",
        "MTTR_response<1000ms": m.mttr_response_ms < 1000,
        "SW>=0.80": m.social_welfare >= 0.80,
    }
