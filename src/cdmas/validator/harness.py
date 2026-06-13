"""Deterministic in-process scenario harness (SDD §6.2.3, SRS §8).

Drives the real defense fleet + attackers against an in-process simulator on a ManualClock,
then grades the recorded event log with the FR constraint checkers and the analytics. Fully
deterministic: same seed + same script => identical result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cdmas.agents.attackers.base_attacker import AttackerAgent
from cdmas.agents.factory import build_all
from cdmas.agents.raa.agent import ResourceAllocatorAgent
from cdmas.analytics.metrics import compute_metrics
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.logging.event_log import EventLog, EventType, InMemorySink
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.models.enums import Segment
from cdmas.common.models.metrics import MetricsSnapshot
from cdmas.common.timing.clock import ManualClock
from cdmas.coordination.failure import FailoverCoordinator, HeartbeatMonitor
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.sampling import PacketSampler, correlate_alert_ms
from cdmas.validator.constraints import CheckContext, ConstraintResult, check_all

_STEP_MS = 50
_NOMINAL_DURATION_MS = 60_000.0


@dataclass
class ScenarioResult:
    events: list[EventLog]
    metrics: MetricsSnapshot
    constraints: list[ConstraintResult]
    segments: list[Segment]
    packets: list[dict[str, Any]] = field(default_factory=list)  # dashboard packet sample
    messages: list[dict[str, Any]] = field(default_factory=list)  # dashboard ACL stream

    @property
    def failed(self) -> list[ConstraintResult]:
        return [c for c in self.constraints if c.status == "FAIL"]

    @property
    def passed(self) -> bool:
        return not self.failed


class ScenarioHarness:
    def __init__(
        self, *, segments: list[Segment], seed: int = 0, quarantine_slots: int = 4
    ) -> None:
        self.clock = ManualClock()
        self.bus = InMemoryBus()
        self.sink = InMemorySink()
        self.sampler = PacketSampler()
        self.sim = InProcessSimulator(
            clock=self.clock, segments=segments, seed=seed, sampler=self.sampler
        )
        self.agents = build_all(segments, self.bus, self.sim, self.sink, self.clock)
        for agent in self.agents:
            if isinstance(agent, ResourceAllocatorAgent):
                agent.quarantine_slots = quarantine_slots
            agent.setup()
        self.attackers: list[AttackerAgent] = []
        self._monitor = HeartbeatMonitor()
        self._failover = FailoverCoordinator(self._monitor, self.sink)
        self._dead: set[str] = set()

    def add_attacker(self, attacker: AttackerAgent) -> None:
        attacker.setup()
        self.attackers.append(attacker)

    def inject(self, spec: AttackSpec) -> None:
        self.sim.inject(spec)

    async def warmup(self, rounds: int = 30) -> None:
        for _ in range(rounds):
            self.sim.tick()
            for agent in self.agents:
                await agent.step()
            self.clock.advance(_STEP_MS)

    async def run(
        self, rounds: int = 40, *, fail_agent: str | None = None, fail_after_rounds: int = 0
    ) -> None:
        failed_type = fail_agent.split(":")[0] if fail_agent else None
        for r in range(rounds):
            if fail_agent and r == fail_after_rounds:
                self._dead.add(fail_agent)
            self.sim.tick()
            for agent in self.agents:
                if agent.agent_id in self._dead:
                    continue
                await agent.step()
                self._monitor.beat(agent.agent_id, self.clock.now_ms())
            for attacker in self.attackers:
                await attacker.step()
            if fail_agent:
                segment_of = {
                    a.agent_id: a.segment
                    for a in self.agents
                    if a.agent_id == fail_agent and a.segment
                }
                loads = {
                    a.agent_id: 0.1
                    for a in self.agents
                    if a.agent_type == failed_type and a.agent_id not in self._dead
                }
                await self._failover.check(self.clock.now_ms(), segment_of, loads)
            self.clock.advance(_STEP_MS)

    def evaluate(self, *, total_time_ms: float = _NOMINAL_DURATION_MS) -> ScenarioResult:
        metrics = compute_metrics(
            self.sink.events,
            self.sim.ground_truth(),
            segment_count=len(self.sim.segments),
            total_time_ms=total_time_ms,
        )
        constraints = check_all(CheckContext(events=self.sink.events, metrics=metrics))
        packets = self.sampler.export()
        correlate_alert_ms(packets, self._alerts_by_segment())
        return ScenarioResult(
            self.sink.events,
            metrics,
            constraints,
            list(self.sim.segments),
            packets=packets,
        )

    def _alerts_by_segment(self) -> dict[str, list[float]]:
        alerts: dict[str, list[float]] = {}
        for e in self.sink.events:
            if e.event_type is EventType.ALERT_PUBLISHED and e.segment is not None:
                alerts.setdefault(e.segment, []).append(e.wall_ms)
        for times in alerts.values():
            times.sort()
        return alerts


def all_agents(harness: ScenarioHarness) -> list[BaseAgent]:
    return harness.agents
