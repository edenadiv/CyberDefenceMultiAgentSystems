from datetime import datetime, timezone

from cdmas.common.models.bid import AuctionResult, ResourceBid
from cdmas.common.models.coalition import CoalitionInvite, CoalitionRecord
from cdmas.common.models.enums import ResourceType, ResponseType, Segment, VoteDecision
from cdmas.common.models.errors import Failure, NotUnderstood
from cdmas.common.models.resolution import ResolutionNotice
from cdmas.common.models.vote import VoteRequest, VoteResponse


def test_bid_and_result():
    bid = ResourceBid(
        bidder_id="RCA:seg1",
        resource_type=ResourceType.QUARANTINE_SLOT,
        quantity=1,
        bid_value=0.91,
        justification_threat_id="t1",
    )
    assert bid.bid_id
    res = AuctionResult(granted={"RCA:seg1": 1}, denied=["RCA:seg2"])
    assert res.granted["RCA:seg1"] == 1
    assert "RCA:seg2" in res.denied


def test_vote_pair():
    req = VoteRequest(
        proposal=ResponseType.QUARANTINE,
        target_segment=Segment.SERVER,
        threat_id="t1",
        severity=0.85,
        deadline=datetime.now(timezone.utc),
    )
    resp = VoteResponse(
        vote_id=req.vote_id, voter_id="ACA:seg2", decision=VoteDecision.ACCEPT, rationale="local=0.88"
    )
    assert resp.vote_id == req.vote_id
    assert resp.decision is VoteDecision.ACCEPT


def test_coalition_and_resolution():
    inv = CoalitionInvite(threat_id="t1", segments=[Segment.SERVER, Segment.INTERNAL], required_roles=["ACA", "RCA"])
    rec = CoalitionRecord(coalition_id=inv.coalition_id, members=["ACA:seg1", "RCA:seg1"], lead_rca="RCA:seg1", threat_id="t1")
    assert rec.coalition_id == inv.coalition_id
    note = ResolutionNotice(threat_id="t1", segment=Segment.SERVER, outcome="neutralized")
    assert note.resolution_id


def test_error_payloads():
    f = Failure(in_reply_to="m1", sender="RCA:1", receiver="RAA:1", reason="TIMEOUT", failed_action="QUARANTINE", description="vote deadline exceeded", fallback_action="BLOCK")
    assert f.fallback_action == "BLOCK"
    nu = NotUnderstood(in_reply_to="m1", sender="ACA:2", receiver="TMA:1", reason="SCHEMA_VIOLATION", offending_field="anomaly_type", description="unknown enum")
    assert nu.offending_field == "anomaly_type"
