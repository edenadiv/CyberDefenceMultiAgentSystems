from cdmas.common.models.enums import VoteDecision
from cdmas.coordination.auction import Bid, run_auction
from cdmas.coordination.coalition import CoalitionState, evaluate_invitation
from cdmas.coordination.failure import HeartbeatMonitor, select_failover_peer
from cdmas.coordination.voting import evaluate_vote, majority_threshold, tally


# --- auction (FR-19, FR-20) ---
def test_auction_grants_top_severities():
    bids = [
        Bid("RCA:1", 0.9, 0.0),
        Bid("RCA:2", 0.5, 0.0),
        Bid("RCA:3", 0.7, 0.0),
        Bid("RCA:4", 0.2, 0.0),
        Bid("RCA:5", 0.8, 0.0),
    ]
    outcome = run_auction(bids, slots=3)
    assert set(outcome.granted) == {"RCA:1", "RCA:5", "RCA:3"}  # top-3 severities
    assert set(outcome.denied) == {"RCA:2", "RCA:4"}


def test_auction_tie_broken_by_earliest():
    bids = [Bid("A", 0.8, 5.0), Bid("B", 0.8, 1.0)]
    assert run_auction(bids, slots=1).granted == ["B"]  # earlier submission wins


# --- voting (FR-11) ---
def test_evaluate_vote_thresholds():
    assert evaluate_vote(0.9, 0.1) is VoteDecision.ACCEPT
    assert evaluate_vote(0.5, 0.1) is VoteDecision.REJECT  # not severe enough
    assert evaluate_vote(0.9, 0.95) is VoteDecision.REJECT  # overloaded


def test_majority_and_tally():
    assert majority_threshold(5) == 3
    assert majority_threshold(4) == 3
    votes = {"a": VoteDecision.ACCEPT, "b": VoteDecision.ACCEPT, "c": VoteDecision.REJECT}
    assert tally(votes, member_count=5) is False  # 2 < 3
    votes["d"] = VoteDecision.ACCEPT
    assert tally(votes, member_count=5) is True  # 3 >= 3


# --- coalition (FR-16, FR-17) ---
def test_coalition_accumulates_and_picks_lead_rca():
    cs = CoalitionState(
        coalition_id="c1",
        threat_id="t1",
        segments=["public-facing", "internal"],
        invited={"ACA:seg1", "RCA:seg1", "RCA:seg2"},
    )
    cs.record("ACA:seg1", True)
    cs.record("RCA:seg2", True)
    cs.record("RCA:seg1", False)
    members = cs.finalize()
    assert set(members) == {"ACA:seg1", "RCA:seg2"}
    assert cs.lead_rca == "RCA:seg2"


def test_evaluate_invitation():
    assert evaluate_invitation(0.3) is True
    assert evaluate_invitation(0.95) is False


# --- failure/resilience (FR-34) ---
def test_heartbeat_monitor_detects_silence():
    mon = HeartbeatMonitor(timeout_ms=1000)
    mon.beat("ACA:seg1", now_ms=0.0)
    mon.beat("ACA:seg2", now_ms=900.0)
    assert mon.failed(now_ms=1500.0) == ["ACA:seg1"]  # seg1 silent >1s, seg2 ok


def test_select_min_load_peer():
    assert select_failover_peer({"a": 0.7, "b": 0.2, "c": 0.5}) == "b"
    assert select_failover_peer({}) is None
