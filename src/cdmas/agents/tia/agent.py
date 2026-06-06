"""Threat Intelligence Agent — global threat map, correlation, priority ranking.

Phase 3 builds the map, emits model-update/correlation/priority telemetry. Coalition
formation on detected multi-segment correlation is wired in Phase 4.
"""

from __future__ import annotations

from uuid import uuid4

from cdmas.agents.tia.threat_map import GlobalThreatMap, ThreatEntry
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative, Segment
from cdmas.common.timing.clock import Clock

_RANK_INTERVAL_MS = 1000.0


class ThreatIntelligenceAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.map = GlobalThreatMap()
        self._new_reports = False
        self._last_rank_ms = -1e9
        self._reported_correlations: set[frozenset[Segment]] = set()

    def setup(self) -> None:
        self.subscribe(Topic.THREAT_REPORTS)
        self.subscribe(Topic.THREAT_INTEL)
        self.goals.add(Goal(description="maintain global intel", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="intel_cycle",
                trigger=lambda b: True,
                precondition=lambda b: True,
                body=self._cycle,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic is not Topic.THREAT_REPORTS:
            return
        threat = message.content.get("threat")
        if not threat:
            return
        ts = message.content.get("ts_ms", self.now_ms())
        self.map.add(
            ThreatEntry(
                threat_id=threat["threat_id"],
                segment=Segment(threat["segment"]),
                severity=threat["severity"],
                ts_ms=ts,
                attack_type=threat["attack_type"],
            )
        )
        self.beliefs.revise(Belief(predicate="last_report_ts", value=ts, source=message.sender))
        self._new_reports = True

    async def _cycle(self, _agent: BaseAgent) -> None:
        now = self.now_ms()
        if self._new_reports:
            self._new_reports = False
            last_ts = self.beliefs.value("last_report_ts", now)
            active = self.map.active_segments(now)
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={
                    "signal": "threat_model_update",
                    "segments": sorted(s.value for s in active),
                },
                latency_ms=int(now - last_ts),
            )
            await self._detect_correlation(now, active)
        if now - self._last_rank_ms >= _RANK_INTERVAL_MS:
            self._last_rank_ms = now
            priority = self.map.priority_list()
            await self.publish(
                ACLMessage(
                    performative=Performative.INFORM,
                    sender=self.agent_id,
                    receiver="BROADCAST",
                    topic=Topic.THREAT_INTEL,
                    content={
                        "signal": "priority_list",
                        "priority": [e.threat_id for e in priority],
                        "ts_ms": now,
                    },
                )
            )
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={"signal": "priority_list", "count": len(priority)},
            )

    async def _detect_correlation(self, now: float, active: set[Segment]) -> None:
        if len(active) < 2:
            return
        key = frozenset(active)
        if key in self._reported_correlations:
            return
        self._reported_correlations.add(key)
        last_ts = self.beliefs.value("last_report_ts", now)
        await self.log_event(
            EventType.ACTION_EXECUTED,
            payload={"signal": "correlation", "segments": sorted(s.value for s in active)},
            latency_ms=int(now - last_ts),
        )
        await self._form_coalition(now, active, last_ts)

    async def _form_coalition(self, now: float, active: set[Segment], last_ts: float) -> None:
        coalition_id = str(uuid4())
        members = sorted(f"RCA:{s.value}" for s in active)
        lead = members[0] if members else None
        await self.publish(
            ACLMessage(
                performative=Performative.REQUEST,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.COALITION,
                content={
                    "coalition": {
                        "coalition_id": coalition_id,
                        "members": members,
                        "lead_rca": lead,
                        "segments": sorted(s.value for s in active),
                    },
                    "ts_ms": now,
                },
            )
        )
        await self.log_event(
            EventType.COALITION_FORMED,
            payload={
                "coalition_id": coalition_id,
                "members": members,
                "lead_rca": lead,
                "segments": sorted(s.value for s in active),
            },
            latency_ms=int(now - last_ts),
        )
