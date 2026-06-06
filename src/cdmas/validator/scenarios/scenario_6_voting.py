"""Scenario 6 - Voting Protocol Validation (SRS §8.6).

A multi-segment host compromise forms a coalition; the lead RCA escalates QUARANTINE, which
only executes after a majority coalition vote.
"""

from __future__ import annotations

from cdmas.agents.attackers.lateral import LateralMovementAgent
from cdmas.common.models.enums import Segment
from cdmas.validator.harness import ScenarioHarness, ScenarioResult


async def run() -> ScenarioResult:
    h = ScenarioHarness(segments=[Segment.SERVER, Segment.INTERNAL], seed=6)
    h.add_attacker(
        LateralMovementAgent(
            "ATK:lat1", "server", h.bus, h.sim, h.sink, clock=h.clock, intensity=5.0
        )
    )
    h.add_attacker(
        LateralMovementAgent(
            "ATK:lat2", "internal", h.bus, h.sim, h.sink, clock=h.clock, intensity=5.0
        )
    )
    await h.warmup(30)
    await h.run(50)
    return h.evaluate()


def criteria(r: ScenarioResult) -> dict[str, bool]:
    m = r.metrics
    by_fr = {c.fr_id: c for c in r.constraints}
    return {
        "quarantine_after_majority": by_fr["FR-11"].status == "PASS",
        "vote<300ms": _max_vote_latency(r) < 300,
        "SW>=0.80": m.social_welfare >= 0.80,
    }


def _max_vote_latency(r: ScenarioResult) -> float:
    from cdmas.common.logging.event_log import EventType

    votes = [
        e.latency_ms
        for e in r.events
        if e.event_type is EventType.VOTE_CAST and e.latency_ms is not None
    ]
    return max(votes) if votes else 0.0
