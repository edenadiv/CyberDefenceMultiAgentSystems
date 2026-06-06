"""Traffic Monitor Agent — samples traffic, flags >2-sigma anomalies, alerts <100ms."""

from __future__ import annotations

from cdmas.agents._common.features import extract_features
from cdmas.agents.tma.baseline import RollingBaseline
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.alert import Alert
from cdmas.common.models.enums import AttackType, Performative, Segment
from cdmas.common.timing.clock import Clock
from cdmas.simulator.client import SimClientProtocol

_ALERT_SIGMA = 2.0
_TELEMETRY_INTERVAL_MS = 1000.0


class TrafficMonitorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        sim: SimClientProtocol,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.sim = sim
        self.baseline = RollingBaseline()
        self._seg = Segment(segment) if segment else Segment.PUBLIC_FACING
        self._last_sampling_ms = -1e9
        self._last_baseline_ms = -1e9

    def setup(self) -> None:
        self.goals.add(Goal(description="detect anomalies", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="publish_alert",
                trigger=lambda b: b.value("pending_alert") is not None,
                precondition=lambda b: True,
                body=self._publish_alert,
            )
        )

    async def sense(self) -> None:
        pkts = await self.sim.get_packets(self._seg, 2000)
        if not pkts:
            return
        volume = sum(p.freq for p in pkts)
        deviation = self.baseline.deviation(volume)
        now = self.now_ms()
        await self._emit_sampling(now)
        if deviation > _ALERT_SIGMA:
            alert = Alert(
                segment=self._seg,
                anomaly_type=AttackType.VOLUME_SPIKE,
                deviation_score=deviation,
                src_ips=sorted({p.src_ip for p in pkts})[:20],
                dst_port=pkts[0].port,
                traffic_volume=volume,
                baseline_mean=self.baseline.mean,
                baseline_std=self.baseline.std,
            )
            self.beliefs.revise(
                Belief(
                    predicate="pending_alert",
                    value={"alert": alert, "features": extract_features(pkts), "ts_ms": now},
                    source=self.agent_id,
                )
            )
        else:
            self.baseline.update(volume)
            await self._emit_baseline(now)

    async def _emit_sampling(self, now: float) -> None:
        if now - self._last_sampling_ms >= _TELEMETRY_INTERVAL_MS:
            self._last_sampling_ms = now
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={"signal": "sampling", "sample_rate_hz": 100.0, "segment": self._seg.value},
            )

    async def _emit_baseline(self, now: float) -> None:
        if now - self._last_baseline_ms >= _TELEMETRY_INTERVAL_MS:
            self._last_baseline_ms = now
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={
                    "signal": "baseline_update",
                    "segment": self._seg.value,
                    "mean": self.baseline.mean,
                },
            )

    async def _publish_alert(self, _agent: BaseAgent) -> None:
        pending = self.beliefs.value("pending_alert")
        alert: Alert = pending["alert"]
        ts_ms: float = pending["ts_ms"]
        now = self.now_ms()
        await self.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.ALERTS,
                content={
                    "alert": alert.model_dump(mode="json"),
                    "features": pending["features"],
                    "ts_ms": now,
                },
            )
        )
        await self.log_event(
            EventType.ALERT_PUBLISHED,
            payload={
                "signal": "alert",
                "segment": self._seg.value,
                "alert_id": alert.alert_id,
                "deviation_score": alert.deviation_score,
            },
            latency_ms=int(now - ts_ms),
        )
        self.beliefs.revise(Belief(predicate="pending_alert", value=None, source=self.agent_id))

    async def step(self) -> None:
        await self.sense()
        await super().step()
