"""Coalition formation for multi-segment incidents (SDD §4.3, Figure 8).

The TIA invites agents covering the affected segments; those not overloaded accept within
200ms. A lead RCA is designated. An agent may belong to at most one coalition at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

COALITION_REPLY_MS = 200.0
_DEFAULT_LOAD_THRESHOLD = 0.8


def evaluate_invitation(local_load: float, load_threshold: float = _DEFAULT_LOAD_THRESHOLD) -> bool:
    """An agent accepts a coalition invitation if it is not already overloaded."""
    return local_load < load_threshold


@dataclass
class CoalitionState:
    coalition_id: str
    threat_id: str
    segments: list[str]
    invited: set[str]
    accepted: set[str] = field(default_factory=set)
    lead_rca: str | None = None

    def record(self, agent_id: str, accept: bool) -> None:
        if accept and agent_id in self.invited:
            self.accepted.add(agent_id)

    def finalize(self) -> list[str]:
        """Confirm membership and designate the first accepting RCA as lead."""
        members = sorted(self.accepted)
        rcas = [m for m in members if m.split(":")[0] == "RCA"]
        self.lead_rca = rcas[0] if rcas else (members[0] if members else None)
        return members
