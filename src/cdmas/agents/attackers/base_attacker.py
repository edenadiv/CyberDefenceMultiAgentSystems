"""Base attacker agent — injects an attack into the simulator and logs its action.

Attackers act through the simulator (not the defense bus). Each logs an ``attack_action``
event (FR-27) carrying the details the validator checks (randomized IPs, scan ports, mode).
"""

from __future__ import annotations

from typing import Any, Protocol

from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import EventSink, EventType
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import Clock
from cdmas.simulator.attacks import AttackSpec


class AttackChannel(Protocol):
    def inject(self, spec: AttackSpec) -> None: ...


class AttackerAgent(BaseAgent):
    attack_type: AttackType = AttackType.NOVEL

    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        sim: AttackChannel,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
        intensity: float = 2.0,
        mode: str = "independent",
        seed: int = 0,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.sim = sim
        self._target = Segment(segment) if segment else Segment.PUBLIC_FACING
        self.intensity = intensity
        self.mode = mode
        self.seed = seed
        self._launched = False

    def setup(self) -> None:
        self.goals.add(Goal(description="disrupt the network", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="execute_attack",
                trigger=lambda b: not self._launched,
                precondition=lambda b: True,
                body=self._execute,
            )
        )

    def _action_payload(self) -> dict[str, Any]:
        """Type-specific telemetry. Overridden by subclasses."""
        return {}

    async def _execute(self, _agent: BaseAgent) -> None:
        self._launched = True
        spec = AttackSpec(
            type=self.attack_type,
            segment=self._target,
            intensity=self.intensity,
            mode=self.mode,
        )
        self.sim.inject(spec)
        payload: dict[str, Any] = {
            "signal": "attack_action",
            "attack_type": self.attack_type.value,
            "segment": self._target.value,
            "mode": self.mode,
            "intensity": self.intensity,
        }
        payload.update(self._action_payload())
        await self.log_event(EventType.ACTION_EXECUTED, payload=payload)
