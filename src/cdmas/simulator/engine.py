"""In-process simulation engine composing every component (SDD §6.1).

Implements the ``SimClientProtocol`` (defined in client.py) so agents and the validator
harness can drive it directly, with no HTTP. The FastAPI layer (api.py) wraps the same
engine for production.
"""

from __future__ import annotations

from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import Clock
from cdmas.simulator.attacks import AttackInjector, AttackSpec, GroundTruth
from cdmas.simulator.clock import SimClock
from cdmas.simulator.models import (
    ActionRequest,
    ActionResult,
    SegmentState,
    StateSnapshot,
    TopologyView,
)
from cdmas.simulator.packet import Packet
from cdmas.simulator.resources import ResourcePool
from cdmas.simulator.sampling import PacketSampler
from cdmas.simulator.state import StateManager
from cdmas.simulator.topology import NetworkTopology
from cdmas.simulator.traffic import TrafficGenerator

_THROTTLE_FACTOR = 0.2  # malicious volume retained while THROTTLE is active
_PACKETS_PER_TICK = 50


class InProcessSimulator:
    def __init__(
        self,
        *,
        clock: Clock,
        segments: list[Segment] | None = None,
        seed: int = 0,
        speed: float = 1.0,
        tick_ms: int = 10,
        resource_pool: ResourcePool | None = None,
        sampler: PacketSampler | None = None,
    ) -> None:
        self.clock = clock
        self.segments = segments if segments is not None else list(Segment)
        self.topology = NetworkTopology(self.segments)
        self.simclock = SimClock(clock, speed=speed, tick_ms=tick_ms)
        self.traffic = TrafficGenerator(seed=seed)
        self.injector = AttackInjector(seed=seed + 1, topology=self.topology)
        self.state = StateManager(self.topology)
        self.resources = resource_pool or ResourcePool()
        self.sampler = sampler  # optional dashboard packet capture (validator path only)
        self._last: dict[Segment, list[Packet]] = {s: [] for s in self.segments}

    # --- environment driving ---------------------------------------------
    def tick(self) -> None:
        now = self.simclock.sim_now_ms()
        for seg in self.segments:
            base = self.traffic.sample(seg, _PACKETS_PER_TICK, ts_ms=now)
            malicious = self.injector.overlay(seg, now)
            if self.sampler is not None:
                # Capture the *real* attack burst before throttle/quarantine attenuates it.
                self.sampler.observe(seg, now, base, malicious)
            if malicious and not self.state.is_quarantined(seg):
                self.state.mark_under_attack(seg)
            defenses = self.state.active_defenses(seg)
            if "THROTTLE" in defenses or "BLOCK" in defenses:
                malicious = [
                    p.model_copy(update={"freq": p.freq * _THROTTLE_FACTOR}) for p in malicious
                ]
            if self.state.is_quarantined(seg):
                malicious = []  # isolated
            self._last[seg] = base + malicious

    def inject(self, spec: AttackSpec) -> None:
        self.injector.inject(spec)

    def ground_truth(self) -> GroundTruth:
        return self.injector.ground_truth()

    # --- SimClientProtocol -----------------------------------------------
    async def get_packets(self, segment: Segment, n: int) -> list[Packet]:
        return self._last.get(segment, [])[:n]

    async def apply_action(self, req: ActionRequest) -> ActionResult:
        return self.state.apply_action(req)

    async def get_topology(self) -> TopologyView:
        return TopologyView(segments=list(self.segments), adjacency=self.topology.adjacency_view())

    async def get_state(self) -> StateSnapshot:
        segs = [
            SegmentState(
                segment=s,
                health=self.state.health(s),
                flows_per_s=sum(p.freq for p in self._last.get(s, [])),
                active_defenses=self.state.active_defenses(s),
            )
            for s in self.segments
        ]
        return StateSnapshot(
            sim_ms=self.simclock.sim_now_ms(),
            segments=segs,
            resource_overhead=self.resources.utilization(),
        )
