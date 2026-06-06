"""Protocols wired through real agents on the in-memory bus."""

from cdmas.agents.raa.agent import ResourceAllocatorAgent
from cdmas.agents.rca.agent import ResponseCoordinatorAgent
from cdmas.agents.tia.agent import ThreatIntelligenceAgent
from cdmas.common.logging.event_log import EventType, InMemorySink
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.coordination.failure import FailoverCoordinator, HeartbeatMonitor
from cdmas.simulator.engine import InProcessSimulator


def _confirmed(threat_id: str, seg: str, sev: float, attack_type: str = "DDOS") -> dict:
    return {
        "threat_id": threat_id,
        "classification": "CONFIRMED_THREAT",
        "attack_type": attack_type,
        "severity": sev,
        "segment": seg,
        "confidence": 0.95,
    }


async def test_auction_allocates_top_severity_slots():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.SERVER], seed=0)
    bus = InMemoryBus()
    raa = ResourceAllocatorAgent("RAA:global", None, bus, sim, clock=clk, quarantine_slots=2)
    raa.setup()
    for bidder, value in [("RCA:1", 0.9), ("RCA:2", 0.4), ("RCA:3", 0.7)]:
        await bus.publish(
            ACLMessage(
                performative=Performative.BID,
                sender=bidder,
                receiver="RAA:global",
                topic=Topic.RESOURCE_BIDS,
                content={"bid": {"bidder_id": bidder, "bid_value": value}, "ts_ms": 0.0},
            )
        )
    await raa.step()
    auctions = [e for e in raa.sink.events if e.event_type is EventType.AUCTION_COMPLETED]
    assert auctions
    assert set(auctions[-1].payload["granted"]) == {"RCA:1", "RCA:3"}  # top-2 severities
    assert auctions[-1].latency_ms is not None and auctions[-1].latency_ms < 300


async def test_quarantine_requires_majority_vote():
    clk = ManualClock()
    sim = InProcessSimulator(clock=clk, segments=[Segment.SERVER], seed=0)
    bus = InMemoryBus()
    sink = InMemorySink()
    members = ["RCA:a", "RCA:b", "RCA:c"]
    rcas = [
        ResponseCoordinatorAgent(mid, "server", bus, sim, sink, clock=clk, voters=members)
        for mid in members
    ]
    for r in rcas:
        r.setup()

    # A severe host compromise to the lead -> proportional action is QUARANTINE -> vote.
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="ACA:server",
            receiver="RCA:a",  # only the lead handles it; b and c are pure voters
            topic=Topic.THREAT_REPORTS,
            content={"threat": _confirmed("t1", "server", 0.95, "LATERAL"), "ts_ms": 0.0},
        )
    )
    # Run several rounds for request -> responses -> tally.
    for _ in range(5):
        for r in rcas:
            await r.step()
        clk.advance(10)

    votes = [e for e in sink.events if e.event_type is EventType.VOTE_CAST]
    quarantines = [
        e
        for e in sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("action") == "QUARANTINE"
    ]
    assert votes and votes[-1].payload["approved"] is True
    assert votes[-1].payload["accept_count"] >= 2  # majority of 3
    assert quarantines  # quarantine executed after the vote


async def test_tia_forms_coalition_on_correlation():
    clk = ManualClock()
    bus = InMemoryBus()
    tia = ThreatIntelligenceAgent("TIA:global", None, bus, clock=clk)
    tia.setup()
    for seg in ("public-facing", "internal"):
        await bus.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender=f"ACA:{seg}",
                receiver="BROADCAST",
                topic=Topic.THREAT_REPORTS,
                content={"threat": _confirmed(f"t-{seg}", seg, 0.9), "ts_ms": 0.0},
            )
        )
    await tia.step()
    coalitions = [e for e in tia.sink.events if e.event_type is EventType.COALITION_FORMED]
    assert coalitions
    assert coalitions[-1].latency_ms is not None and coalitions[-1].latency_ms < 1000
    assert set(coalitions[-1].payload["members"]) == {"RCA:public-facing", "RCA:internal"}


async def test_failover_reassigns_coverage_within_2s():
    sink = InMemorySink()
    monitor = HeartbeatMonitor(timeout_ms=1000)
    coord = FailoverCoordinator(monitor, sink)
    monitor.beat("ACA:server", now_ms=0.0)
    monitor.beat("ACA:public-facing", now_ms=0.0)
    # server ACA goes silent; detected at t=1500.
    monitor.beat("ACA:public-facing", now_ms=1400.0)
    await coord.check(
        now_ms=1500.0,
        segment_of={"ACA:server": "server"},
        loads={"ACA:public-facing": 0.3},
    )
    failed = [e for e in sink.events if e.event_type is EventType.AGENT_FAILED]
    reassigned = [
        e
        for e in sink.events
        if e.event_type is EventType.ACTION_EXECUTED
        and e.payload.get("signal") == "coverage_reassigned"
    ]
    assert failed and failed[-1].payload["failed_agent"] == "ACA:server"
    assert reassigned and reassigned[-1].payload["new_owner"] == "ACA:public-facing"
    assert reassigned[-1].latency_ms is not None and reassigned[-1].latency_ms < 2000
