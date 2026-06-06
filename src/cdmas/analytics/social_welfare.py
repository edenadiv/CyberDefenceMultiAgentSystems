"""Social Welfare: the weighted aggregate of agent utilities (SRS §7.2)."""

from __future__ import annotations

# Weights per SRS §7.2 (sum to 1.0).
WEIGHTS: dict[str, float] = {
    "TMA": 0.20,
    "ACA": 0.30,
    "RCA": 0.25,
    "RAA": 0.10,
    "TIA": 0.15,
}

SW_THRESHOLD = 0.80


def social_welfare(utilities: dict[str, float]) -> float:
    return round(sum(WEIGHTS[a] * utilities.get(a, 0.0) for a in WEIGHTS), 4)
