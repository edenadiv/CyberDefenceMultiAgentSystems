"""Voting-based quarantine escalation (SDD §4.4, Figures 9-10).

A quarantine requires majority approval (>50%) of the coalition within a 300ms window.
Non-responders are counted as REJECT so the protocol always terminates; on failure to reach
majority the coalition falls back to BLOCK.
"""

from __future__ import annotations

from cdmas.common.models.enums import VoteDecision

VOTE_DEADLINE_MS = 300.0
_LOCAL_SEVERITY_THRESHOLD = 0.7


def evaluate_vote(
    local_severity: float, local_load: float, load_threshold: float = 0.8
) -> VoteDecision:
    """A member approves a quarantine if it locally agrees the threat is severe and it is
    not overloaded (SDD Figure 10)."""
    if local_severity >= _LOCAL_SEVERITY_THRESHOLD and local_load < load_threshold:
        return VoteDecision.ACCEPT
    return VoteDecision.REJECT


def majority_threshold(member_count: int) -> int:
    """Votes required to pass: floor(n/2) + 1."""
    return member_count // 2 + 1


def tally(votes: dict[str, VoteDecision], member_count: int) -> bool:
    """True if the quarantine is approved by a strict majority of the coalition."""
    accept = sum(1 for v in votes.values() if v is VoteDecision.ACCEPT)
    return accept >= majority_threshold(member_count)
