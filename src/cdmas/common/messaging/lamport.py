"""Lamport logical clock for total message ordering (SDD §3.1.3)."""


class LamportClock:
    def __init__(self, initial: int = 0) -> None:
        self._time = initial

    @property
    def time(self) -> int:
        return self._time

    def tick(self) -> int:
        """Local event (e.g. a send). Increment and return."""
        self._time += 1
        return self._time

    def update(self, received: int) -> int:
        """Receive event. Advance past the received timestamp."""
        self._time = max(self._time, received) + 1
        return self._time
