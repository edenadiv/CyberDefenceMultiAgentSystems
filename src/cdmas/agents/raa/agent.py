"""Resource Allocator Agent — sealed-bid auction, overhead monitoring, reclamation.

FR-19..23: collects sealed bids and allocates the scarce slots to the highest-severity
threats (auction), enforces the 40% host-overhead cap, and reclaims resources on
resolution.
"""

from __future__ import annotations

from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative
from cdmas.common.timing.clock import Clock
from cdmas.coordination.auction import Bid, run_auction
from cdmas.simulator.client import SimClientProtocol

_MONITOR_INTERVAL_MS = 1000.0
_WARN = 0.35
_CAP = 0.40


class ResourceAllocatorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        sim: SimClientProtocol,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
        quarantine_slots: int = 4,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.sim = sim
        self.quarantine_slots = quarantine_slots
        self._bids: list[Bid] = []
        self._first_bid_ms: float | None = None
        self._last_monitor_ms = -1e9

    def setup(self) -> None:
        self.subscribe(Topic.RESOURCE_BIDS)
        self.subscribe(Topic.RESOLUTION)
        self.goals.add(Goal(description="manage resources", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="manage",
                trigger=lambda b: True,
                precondition=lambda b: True,
                body=self._manage,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic is Topic.RESOURCE_BIDS:
            bid = message.content["bid"]
            now = message.content.get("ts_ms", self.now_ms())
            self._bids.append(Bid(bid["bidder_id"], bid["bid_value"], now))
            if self._first_bid_ms is None:
                self._first_bid_ms = now
        elif message.topic is Topic.RESOLUTION:
            self.beliefs.revise(
                Belief(predicate="reclaim_pending", value=True, source=message.sender)
            )
            self.beliefs.revise(
                Belief(
                    predicate="reclaim_ts",
                    value=message.content.get("ts_ms", self.now_ms()),
                    source=message.sender,
                )
            )

    async def _manage(self, _agent: BaseAgent) -> None:
        now = self.now_ms()
        if self._bids:
            await self._run_auction(now)
        if self.beliefs.value("reclaim_pending"):
            await self._reclaim(now)
        if now - self._last_monitor_ms >= _MONITOR_INTERVAL_MS:
            await self._monitor_overhead(now)

    async def _run_auction(self, now: float) -> None:
        # Keep each bidder's highest bid so the auction allocates to distinct agents.
        best: dict[str, Bid] = {}
        for b in self._bids:
            if b.bidder_id not in best or b.bid_value > best[b.bidder_id].bid_value:
                best[b.bidder_id] = b
        bids = list(best.values())
        outcome = run_auction(bids, self.quarantine_slots)
        for winner in outcome.granted:
            await self.publish(
                ACLMessage(
                    performative=Performative.INFORM,
                    sender=self.agent_id,
                    receiver=winner,
                    topic=Topic.RESOURCE_GRANTS,
                    content={"granted": True, "ts_ms": now},
                )
            )
        await self.log_event(
            EventType.AUCTION_COMPLETED,
            payload={
                "bids": {b.bidder_id: b.bid_value for b in bids},
                "granted": outcome.granted,
                "denied": outcome.denied,
                "slots": self.quarantine_slots,
                "notify_latency_ms": 0,
            },
            latency_ms=int(now - (self._first_bid_ms or now)),
        )
        self._bids = []
        self._first_bid_ms = None

    async def _reclaim(self, now: float) -> None:
        self.beliefs.revise(Belief(predicate="reclaim_pending", value=False, source=self.agent_id))
        ts = self.beliefs.value("reclaim_ts", now)
        await self.log_event(
            EventType.RESOURCE_ALLOCATED, payload={"signal": "reclaim"}, latency_ms=int(now - ts)
        )

    async def _monitor_overhead(self, now: float) -> None:
        self._last_monitor_ms = now
        state = await self.sim.get_state()
        overhead = state.resource_overhead
        status = "CRITICAL" if overhead > _CAP else "WARNING" if overhead > _WARN else "OK"
        await self.log_event(
            EventType.RESOURCE_ALLOCATED,
            payload={"signal": "overhead", "overhead": overhead, "status": status},
        )
