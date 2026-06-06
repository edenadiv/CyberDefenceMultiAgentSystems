"""Simulation clock: wraps a base Clock and applies a speed multiplier (SDD §6.1.1)."""

from __future__ import annotations

from cdmas.common.timing.clock import Clock


class SimClock:
    """Maps real (base-clock) elapsed time to simulated time at ``speed`` x.

    speed 1.0 = real time, 0.5 = slow motion, up to 10.0 = accelerated.
    """

    def __init__(self, clock: Clock, *, speed: float = 1.0, tick_ms: int = 10) -> None:
        self._clock = clock
        self.speed = speed
        self.tick_ms = tick_ms
        self._start_wall = clock.now_ms()

    def sim_now_ms(self) -> float:
        return (self._clock.now_ms() - self._start_wall) * self.speed
