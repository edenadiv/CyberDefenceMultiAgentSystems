"""Sealed-bid first-price auction (SDD §4.2, Figure 7).

Bid value equals threat severity, so the highest-severity threats win contested resources.
Single-round, deterministic: ties broken by earliest submission.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bid:
    bidder_id: str
    bid_value: float  # = threat severity, in [0, 1]
    submitted_at: float


@dataclass(frozen=True)
class AuctionOutcome:
    granted: list[str]
    denied: list[str]


def run_auction(bids: list[Bid], slots: int) -> AuctionOutcome:
    """Allocate ``slots`` resources to the highest bids (severity), earliest-first on ties."""
    ranked = sorted(bids, key=lambda b: (-b.bid_value, b.submitted_at))
    granted = [b.bidder_id for b in ranked[:slots]]
    denied = [b.bidder_id for b in ranked[slots:]]
    return AuctionOutcome(granted=granted, denied=denied)
