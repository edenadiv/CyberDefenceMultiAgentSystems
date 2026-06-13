"""Anomaly Classifier Agent — classifies alerts <200ms, online learning, novelty detection."""

from __future__ import annotations

from typing import Any

from cdmas.agents._common.features import FEATURE_NAMES, TRAIN_LABELS, build_training_set
from cdmas.agents.aca.classifier import HybridClassifier
from cdmas.agents.aca.online import OnlineLearner
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import DecisionTrace, EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import AttackType, Classification, Performative, Segment
from cdmas.common.models.threat_report import ThreatReport
from cdmas.common.timing.clock import Clock

_TRAIN_SAMPLES_PER_CLASS = 30


class AnomalyClassifierAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
        classifier: HybridClassifier | None = None,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self._seg = Segment(segment) if segment else Segment.PUBLIC_FACING
        self.classifier = classifier or HybridClassifier()
        self.online = OnlineLearner(self.classifier)
        self._pending: list[dict[str, Any]] = []
        self._recent: dict[str, tuple[list[float], str]] = {}

    def setup(self) -> None:
        self.subscribe(Topic.ALERTS)
        self.subscribe(Topic.RESOLUTION)
        if not self.classifier.is_fitted:
            x, y = build_training_set(
                seed=0, samples_per_class=_TRAIN_SAMPLES_PER_CLASS, segment=self._seg
            )
            self.classifier.fit(x, y)
        self.goals.add(Goal(description="classify threats", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="classify",
                trigger=lambda b: len(self._pending) > 0 or bool(b.value("resolution_pending")),
                precondition=lambda b: True,
                body=self._classify,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic == Topic.ALERTS:
            self._pending.append(
                {
                    "alert": message.content["alert"],
                    "features": message.content["features"],
                    "ts_ms": message.content.get("ts_ms", self.now_ms()),
                }
            )
        elif message.topic == Topic.RESOLUTION:
            self.beliefs.revise(
                Belief(predicate="resolution_pending", value=True, source=message.sender)
            )

    async def _classify(self, _agent: BaseAgent) -> None:
        if self.beliefs.value("resolution_pending"):
            await self._online_learn(_agent)
        while self._pending:
            item = self._pending.pop(0)
            features: list[float] = item["features"]
            ts_ms: float = item["ts_ms"]
            alert: dict[str, Any] = item["alert"]
            verdict = self.classifier.predict(features)
            now = self.now_ms()
            report = ThreatReport(
                alert_id=alert["alert_id"],
                classification=verdict.classification,
                attack_type=verdict.attack_type,
                severity=verdict.severity,
                segment=self._seg,
                confidence=verdict.confidence,
            )
            reported = verdict.classification is not Classification.NORMAL
            if reported:
                await self.publish(
                    ACLMessage(
                        performative=Performative.INFORM,
                        sender=self.agent_id,
                        receiver="BROADCAST",
                        topic=Topic.THREAT_REPORTS,
                        content={"threat": report.model_dump(mode="json"), "ts_ms": now},
                    )
                )
                self._recent[report.threat_id] = (features, verdict.attack_type.value)
            if verdict.attack_type is AttackType.NOVEL and reported:
                await self._share_intel(report, now)
            await self.log_event(
                EventType.THREAT_CLASSIFIED,
                payload={
                    "signal": "classify",
                    "alert_id": alert["alert_id"],
                    "threat_id": report.threat_id,
                    "classification": verdict.classification.value,
                    "attack_type": verdict.attack_type.value,
                    "severity": verdict.severity,
                    "reported": reported,
                },
                latency_ms=int(now - ts_ms),
                decision_trace=DecisionTrace(
                    inputs={"alert_id": alert["alert_id"]},
                    plan_selected="classify",
                    reasoning=f"confidence={verdict.confidence:.2f} novelty={verdict.novelty:.2f}",
                    action="PUBLISH_THREAT_REPORT" if reported else "DROP_NORMAL",
                    confidence=round(verdict.confidence, 4),
                    novelty=round(verdict.novelty, 4),
                    features=[round(f, 4) for f in features],
                    feature_names=FEATURE_NAMES,
                ),
            )

    async def _share_intel(self, report: ThreatReport, now: float) -> None:
        await self.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.THREAT_INTEL,
                content={"threat_id": report.threat_id, "pattern": "NOVEL", "ts_ms": now},
            )
        )

    async def _online_learn(self, _agent: BaseAgent) -> None:
        self.beliefs.revise(
            Belief(predicate="resolution_pending", value=False, source=self.agent_id)
        )
        if not self._recent:
            return
        threat_id = next(reversed(self._recent))
        features, label = self._recent[threat_id]
        if label not in TRAIN_LABELS:
            label = "NORMAL"
        delta = self.online.update(features, label)
        await self.log_event(
            EventType.ACTION_EXECUTED,
            payload={"signal": "online_update", "improvement_rate": delta, "threat_id": threat_id},
        )
