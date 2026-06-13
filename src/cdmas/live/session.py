"""LiveSession — the whole MAS in one process, streamed to the dashboard.

Wires the in-process simulator, an in-memory bus, the real agent fleet (events routed
through a HubSink), and a heartbeat monitor. Drives them in a continuous async loop with
two modes (auto-run / step), and exposes manual actions (send legal / DoS traffic) that the
real agents then detect and respond to. This is the "global vars" live source — no Kafka,
no prebaked replay.
"""

from __future__ import annotations

import asyncio
from typing import Any

from cdmas.agents.factory import build_all
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.models.enums import AttackType, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.coordination.failure import HeartbeatMonitor
from cdmas.live.hub import (
    KIND_CONNECTION_STATUS,
    KIND_SIM_EVENT,
    KIND_SIMULATION_STATE,
    EventHub,
)
from cdmas.live.sink import HubSink
from cdmas.simulator.attacks import AttackSpec
from cdmas.simulator.engine import InProcessSimulator
from cdmas.simulator.sampling import PacketSampler

_STEP_MS = 50  # sim time advanced per round
_INTERVAL_S = 0.12  # real time between rounds (playback pace)


class LiveSession:
    def __init__(
        self,
        *,
        segments: list[Segment],
        hub: EventHub | None = None,
        clock: ManualClock | None = None,
        step_ms: int = _STEP_MS,
        seed: int = 0,
    ) -> None:
        self.hub = hub or EventHub()
        self.clock: ManualClock = clock or ManualClock()
        self.step_ms = step_ms
        self.segments = segments
        self.sampler = PacketSampler()
        self.sim = InProcessSimulator(
            clock=self.clock, segments=segments, seed=seed, sampler=self.sampler
        )
        self.bus = InMemoryBus()
        self.sink = HubSink(self.hub)
        self.agents: list[BaseAgent] = build_all(
            segments, self.bus, self.sim, self.sink, self.clock
        )
        for agent in self.agents:
            agent.setup()
        self.monitor = HeartbeatMonitor()
        self.mode = "auto"
        self.awaiting_next = False
        self._next = asyncio.Event()
        self._running = False
        self._round = 0

    # --- control -----------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        self.mode = "step" if mode == "step" else "auto"
        if self.mode == "auto":
            self._next.set()  # release any pending step gate

    def request_next(self) -> None:
        self._next.set()

    def stop(self) -> None:
        self._running = False
        self._next.set()

    # --- manual actions ----------------------------------------------------
    def send_dos(self, segment: str, intensity: float = 3.0, duration_ms: int = 3000) -> None:
        # Bounded burst: the attack subsides after duration_ms so the segment recovers
        # (an unbounded attack would flood the segment forever).
        now = self.clock.now_ms()
        self.sim.inject(
            AttackSpec(
                type=AttackType.DDOS,
                segment=Segment(segment),
                intensity=intensity,
                start_ms=now,
                duration_ms=duration_ms,
            )
        )
        self.hub.publish(
            KIND_SIM_EVENT,
            {
                "signal": "manual_dos",
                "segment": segment,
                "attack_type": "DDOS",
                "intensity": intensity,
                "duration_ms": duration_ms,
            },
            ts_ms=now,
        )

    def send_legal(self, segment: str, volume: float = 1.0) -> None:
        # Legal traffic is the always-on baseline; announce a pulse so the UI can show
        # green flow without tripping any alert (no attack is injected).
        now = self.clock.now_ms()
        self.hub.publish(
            KIND_SIM_EVENT,
            {"signal": "manual_legal", "segment": segment, "volume": volume},
            ts_ms=now,
        )

    # --- run loop ----------------------------------------------------------
    def topology(self) -> dict[str, Any]:
        return {
            "segments": [s.value for s in self.segments],
            "adjacency": self.sim.topology.adjacency_view(),
        }

    def emit_status(self) -> None:
        self._emit_status(self.clock.now_ms())

    async def tick_round(self) -> None:
        self.sim.tick()
        # Spread the agents across the round (sub-step the clock between them) so the
        # detect -> classify -> respond chain gets realistic, non-zero latencies. The
        # round's total advance is unchanged, so deadlines/cooldowns behave as before.
        sub = self.step_ms / max(1, len(self.agents))
        for agent in self.agents:
            await agent.step()
            self.monitor.beat(agent.agent_id, self.clock.now_ms())
            self.clock.advance(sub)
        self.sim.injector.prune_expired(self.clock.now_ms())  # bound memory on long runs
        self._round += 1
        self._emit_status(self.clock.now_ms())

    def _emit_status(self, now: float) -> None:
        failed = set(self.monitor.failed(now))
        connected = sum(1 for a in self.agents if a.agent_id not in failed)
        self.hub.publish(
            KIND_CONNECTION_STATUS,
            {
                "agents_connected": connected,
                "agents_total": len(self.agents),
                "bus_connected": True,
                "stream_connected": self.hub.subscribers > 0,
            },
            ts_ms=now,
        )
        self.hub.publish(
            KIND_SIMULATION_STATE,
            {
                "mode": self.mode,
                "paused": not self._running,
                "awaiting_next": self.awaiting_next,
                "round": self._round,
            },
            ts_ms=now,
        )

    async def run(self, *, interval_s: float = _INTERVAL_S) -> None:
        self._running = True
        self._emit_status(self.clock.now_ms())
        while self._running:
            if self.mode == "step":
                self.awaiting_next = True
                self._emit_status(self.clock.now_ms())
                await self._next.wait()
                self._next.clear()
                self.awaiting_next = False
                if not self._running:
                    break
            await self.tick_round()  # tick_round advances the clock by one full round
            await asyncio.sleep(interval_s)
