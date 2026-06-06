"""BaseAgent: the BDI perceive->reason->act loop (SDD §2, §5.2)."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from cdmas.common.bdi.belief_base import BeliefBase
from cdmas.common.bdi.goals import GoalSet
from cdmas.common.bdi.plan import Intention, Plan
from cdmas.common.logging.event_log import (
    DecisionTrace,
    EventLog,
    EventSink,
    EventType,
    InMemorySink,
)
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus, Subscription
from cdmas.common.messaging.lamport import LamportClock
from cdmas.common.messaging.topics import Topic
from cdmas.common.timing.clock import Clock, WallClock


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_id.split(":")[0]
        self.segment = segment
        self.bus = bus
        self.beliefs = BeliefBase()
        self.goals = GoalSet()
        self.plans: list[Plan] = []
        self.intention: Intention | None = None
        self.clock = LamportClock()  # logical (causal) clock
        self.timer: Clock = clock or WallClock()  # wall/sim clock for latency measurement
        self.sink: EventSink = event_sink or InMemorySink()
        self._subs: list[Subscription] = []
        self._seq = 0
        self._running = False

    def now_ms(self) -> float:
        return self.timer.now_ms()

    async def log_event(
        self,
        event_type: EventType,
        *,
        payload: dict[str, object] | None = None,
        latency_ms: int | None = None,
        decision_trace: DecisionTrace | None = None,
    ) -> None:
        await self.sink.write(
            EventLog(
                lamport_ts=self.clock.time,
                wall_ms=self.now_ms(),
                event_type=event_type,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                segment=self.segment,
                payload=payload or {},
                latency_ms=latency_ms,
                decision_trace=decision_trace,
            )
        )

    # --- subclass extension points ---------------------------------------
    @abstractmethod
    def setup(self) -> None:
        """Register subscriptions, goals, and plans. Called once before run()."""

    def on_message(self, message: ACLMessage) -> None:
        """Integrate an inbound message into the belief base. Override per agent."""

    # --- bus helpers ------------------------------------------------------
    def subscribe(self, topic: Topic) -> None:
        self._subs.append(self.bus.subscribe(topic, self.agent_id))

    async def publish(self, message: ACLMessage) -> None:
        self._seq += 1
        message.seq = self._seq
        message.sender = self.agent_id
        self.clock.tick()  # local send event
        await self.bus.publish(message)

    # --- BDI loop ---------------------------------------------------------
    async def perceive(self) -> list[ACLMessage]:
        """Drain all currently queued messages from every subscription."""
        percepts: list[ACLMessage] = []
        for sub in self._subs:
            while (msg := sub.get_nowait()) is not None:
                percepts.append(msg)
        return percepts

    def reason(self) -> Intention | None:
        """Pick the first applicable plan, bound to the top active goal."""
        goal = self.goals.top()
        if goal is None:
            return None
        for plan in self.plans:
            if plan.applicable(self.beliefs):
                return Intention(goal=goal, plan=plan, started_at=self.clock.time)
        return None

    async def act(self, intention: Intention) -> None:
        await intention.plan.body(self)

    async def step(self) -> None:
        for msg in await self.perceive():
            self.clock.update(msg.lamport_ts)
            self.on_message(msg)
        intention = self.reason()
        if intention is not None:
            self.intention = intention
            await self.act(intention)

    async def run(self, tick_seconds: float = 0.01) -> None:
        self._running = True
        self.setup()
        while self._running:
            await self.step()
            await asyncio.sleep(tick_seconds)

    def stop(self) -> None:
        self._running = False
