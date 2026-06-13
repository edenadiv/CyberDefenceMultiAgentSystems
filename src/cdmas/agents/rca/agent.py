"""Response Coordinator Agent — proportional response, resource bidding, quarantine voting.

FR-10..14: responds to confirmed threats <500ms with the least-disruptive effective
action; bids for scarce resources; and escalates QUARANTINE through a majority coalition
vote (300ms deadline, BLOCK fallback) before executing it.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from cdmas.agents.rca.policy import (
    ResponseAction,
    proportionality_score,
    select_proportional_action,
)
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import DecisionTrace, EventSink, EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import (
    AttackType,
    Classification,
    Performative,
    ResourceType,
    ResponseType,
    Segment,
    VoteDecision,
)
from cdmas.common.models.resolution import ResolutionNotice
from cdmas.common.timing.clock import Clock
from cdmas.coordination.voting import VOTE_DEADLINE_MS, evaluate_vote, tally
from cdmas.simulator.client import SimClientProtocol
from cdmas.simulator.models import ActionRequest

_SEVERITY_THRESHOLD = 0.7


class ResponseCoordinatorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        segment: str | None,
        bus: MessageBus,
        sim: SimClientProtocol,
        event_sink: EventSink | None = None,
        *,
        clock: Clock | None = None,
        voters: list[str] | None = None,
    ) -> None:
        super().__init__(agent_id, segment, bus, event_sink, clock=clock)
        self.sim = sim
        self.voters = voters or [agent_id]  # coalition members for quarantine votes
        self._pending: list[dict[str, Any]] = []
        self._vote: dict[str, Any] | None = None
        self._outbox_votes: list[dict[str, Any]] = []
        self._quarantined: set[str] = set()

    def setup(self) -> None:
        self.subscribe(Topic.THREAT_REPORTS)
        self.subscribe(Topic.VOTES)
        self.subscribe(Topic.COALITION)
        self.goals.add(Goal(description="coordinate response", priority=1.0))
        self.plans.append(
            Plan(
                plan_id="respond",
                trigger=lambda b: (
                    len(self._pending) > 0 or self._vote is not None or len(self._outbox_votes) > 0
                ),
                precondition=lambda b: True,
                body=self._respond,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        if message.topic is Topic.THREAT_REPORTS:
            threat = message.content["threat"]
            # Each RCA owns its segment's incidents (no cross-segment redundancy).
            if self.segment is not None and threat["segment"] != self.segment:
                return
            if (
                threat["classification"] == Classification.CONFIRMED_THREAT.value
                and threat["severity"] >= _SEVERITY_THRESHOLD
            ):
                self._pending.append(
                    {"threat": threat, "ts_ms": message.content.get("ts_ms", self.now_ms())}
                )
        elif message.topic is Topic.VOTES:
            self._handle_vote_message(message)
        elif message.topic is Topic.COALITION:
            coalition = message.content.get("coalition")
            if coalition and self.agent_id in coalition.get("members", []):
                self.voters = list(coalition["members"])

    def _handle_vote_message(self, message: ACLMessage) -> None:
        req = message.content.get("vote_request")
        if req and message.sender != self.agent_id:
            decision = evaluate_vote(req["severity"], self.beliefs.value("load", 0.1))
            self._reply_vote(req["vote_id"], decision)
        resp = message.content.get("vote_response")
        if resp and self._vote and resp["vote_id"] == self._vote["vote_id"]:
            self._vote["votes"][resp["voter_id"]] = VoteDecision(resp["decision"])

    def _reply_vote(self, vote_id: str, decision: VoteDecision) -> None:
        self._outbox_votes.append(
            {"vote_id": vote_id, "voter_id": self.agent_id, "decision": decision.value}
        )

    async def _respond(self, _agent: BaseAgent) -> None:
        # Send any vote replies queued during perception.
        while self._outbox_votes:
            outbox = self._outbox_votes.pop(0)
            await self.publish(
                ACLMessage(
                    performative=Performative.PROPOSE,
                    sender=self.agent_id,
                    receiver="BROADCAST",
                    topic=Topic.VOTES,
                    content={"vote_response": outbox, "ts_ms": self.now_ms()},
                )
            )
        if self._vote is not None:
            await self._progress_vote()
        while self._pending:
            item = self._pending.pop(0)
            await self._handle_threat(item["threat"], item["ts_ms"])
            if self._vote is not None:
                break  # one quarantine vote at a time

    async def _handle_threat(self, threat: dict[str, Any], ts_ms: float) -> None:
        severity: float = threat["severity"]
        seg = Segment(threat["segment"])
        if seg.value in self._quarantined:
            return  # already contained; no redundant response
        action = select_proportional_action(severity, AttackType(threat["attack_type"]))
        await self._submit_bid(threat, severity)
        if action.type is ResponseType.QUARANTINE:
            await self._start_vote(threat, seg, ts_ms)
            return
        await self._execute(action, action.type, threat, seg, ts_ms)

    async def _submit_bid(self, threat: dict[str, Any], severity: float) -> None:
        await self.publish(
            ACLMessage(
                performative=Performative.BID,
                sender=self.agent_id,
                receiver="RAA:global",
                topic=Topic.RESOURCE_BIDS,
                content={
                    "bid": {
                        "bidder_id": self.agent_id,
                        "resource_type": ResourceType.QUARANTINE_SLOT.value,
                        "bid_value": severity,
                    },
                    "ts_ms": self.now_ms(),
                },
            )
        )

    async def _start_vote(self, threat: dict[str, Any], seg: Segment, ts_ms: float) -> None:
        vote_id = str(uuid4())
        now = self.now_ms()
        self_decision = evaluate_vote(threat["severity"], self.beliefs.value("load", 0.1))
        self._vote = {
            "vote_id": vote_id,
            "members": list(self.voters),
            "votes": {self.agent_id: self_decision},
            "deadline": now + VOTE_DEADLINE_MS,
            "threat": threat,
            "segment": seg,
            "ts_ms": ts_ms,
            "started": now,
        }
        await self.publish(
            ACLMessage(
                performative=Performative.REQUEST,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.VOTES,
                content={
                    "vote_request": {
                        "vote_id": vote_id,
                        "severity": threat["severity"],
                        "segment": seg.value,
                        "threat_id": threat["threat_id"],
                    },
                    "ts_ms": now,
                },
            )
        )

    async def _progress_vote(self) -> None:
        vote = self._vote
        assert vote is not None
        now = self.now_ms()
        complete = len(vote["votes"]) >= len(vote["members"]) or now >= vote["deadline"]
        if not complete:
            return
        for member in vote["members"]:
            vote["votes"].setdefault(member, VoteDecision.REJECT)
        approved = tally(vote["votes"], len(vote["members"]))
        accept_count = sum(1 for v in vote["votes"].values() if v is VoteDecision.ACCEPT)
        await self.log_event(
            EventType.VOTE_CAST,
            payload={
                "vote_id": vote["vote_id"],
                "accept_count": accept_count,
                "member_count": len(vote["members"]),
                "approved": approved,
            },
            latency_ms=int(now - vote["started"]),
            decision_trace=DecisionTrace(
                inputs={"vote_id": vote["vote_id"], "severity": vote["threat"]["severity"]},
                plan_selected="quarantine_vote",
                reasoning=f"{accept_count}/{len(vote['members'])} accept",
                action="QUARANTINE" if approved else "BLOCK_FALLBACK",
                votes={vid: v.value for vid, v in vote["votes"].items()},
            ),
        )
        threat, seg, ts_ms = vote["threat"], vote["segment"], vote["ts_ms"]
        self._vote = None
        if approved:
            action = ResponseAction(ResponseType.QUARANTINE, 0.9)
            await self._execute(
                action, ResponseType.QUARANTINE, threat, seg, ts_ms, vote["vote_id"]
            )
        else:
            action = ResponseAction(ResponseType.BLOCK, 0.5)
            await self.log_event(
                EventType.ACTION_EXECUTED,
                payload={"signal": "vote_failed", "fallback": "BLOCK", "reason": "no_majority"},
            )
            await self._execute(action, ResponseType.BLOCK, threat, seg, ts_ms)

    async def _execute(
        self,
        action: ResponseAction,
        exec_type: ResponseType,
        threat: dict[str, Any],
        seg: Segment,
        ts_ms: float,
        vote_id: str | None = None,
    ) -> None:
        result = await self.sim.apply_action(ActionRequest(type=exec_type, segment=seg))
        if exec_type is ResponseType.QUARANTINE:
            self._quarantined.add(seg.value)
        now = self.now_ms()
        payload: dict[str, Any] = {
            "signal": "response",
            "action": exec_type.value,
            "severity": threat["severity"],
            "segment": seg.value,
            "threat_id": threat["threat_id"],
            "proportionality_score": proportionality_score(action),
            "effectiveness": result.effectiveness,
        }
        if vote_id is not None:
            payload["vote_id"] = vote_id
        await self.log_event(
            EventType.ACTION_EXECUTED,
            payload=payload,
            latency_ms=int(now - ts_ms),
            decision_trace=DecisionTrace(
                inputs={"threat_id": threat["threat_id"], "severity": threat["severity"]},
                plan_selected="respond",
                reasoning=f"least-disruptive effective action for sev={threat['severity']:.2f}",
                action=exec_type.value,
            ),
        )
        await self._resolve_incident(threat, seg, now)

    async def _resolve_incident(self, threat: dict[str, Any], seg: Segment, now: float) -> None:
        notice = ResolutionNotice(threat_id=threat["threat_id"], segment=seg, outcome="neutralized")
        await self.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver="BROADCAST",
                topic=Topic.RESOLUTION,
                content={"resolution": notice.model_dump(mode="json"), "ts_ms": now},
            )
        )
        await self.log_event(
            EventType.INCIDENT_RESOLVED,
            payload={
                "threat_id": threat["threat_id"],
                "resolution_id": notice.resolution_id,
                "segment": seg.value,
            },
        )
