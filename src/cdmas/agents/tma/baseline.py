"""Rolling traffic baseline: mean + std over a recent window (FR-02)."""

from __future__ import annotations

from collections import deque

import numpy as np


class RollingBaseline:
    def __init__(self, window: int = 60, warmup: int = 5) -> None:
        self._w: deque[float] = deque(maxlen=window)
        self.warmup = warmup

    @property
    def mean(self) -> float:
        return float(np.mean(self._w)) if self._w else 0.0

    @property
    def std(self) -> float:
        return float(np.std(self._w)) if len(self._w) > 1 else 0.0

    def update(self, x: float) -> None:
        self._w.append(x)

    def deviation(self, x: float) -> float:
        """Deviation of ``x`` from the baseline in standard deviations."""
        if len(self._w) < self.warmup or self.std == 0.0:
            return 0.0
        return (x - self.mean) / self.std
