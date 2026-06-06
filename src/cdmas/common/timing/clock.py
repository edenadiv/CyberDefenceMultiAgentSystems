"""Clock protocol with a real (wall) and a deterministic (manual) implementation."""

from __future__ import annotations

import asyncio
import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """A source of monotonic milliseconds plus an awaitable sleep."""

    def now_ms(self) -> float: ...

    async def sleep(self, ms: float) -> None: ...


class WallClock:
    """Real time. Production default."""

    def now_ms(self) -> float:
        return time.monotonic() * 1000.0

    async def sleep(self, ms: float) -> None:
        await asyncio.sleep(ms / 1000.0)


class ManualClock:
    """Deterministic time for tests. Time only moves when ``advance`` is called."""

    def __init__(self, start_ms: float = 0.0) -> None:
        self._ms = start_ms
        self._waiters: list[tuple[float, asyncio.Future[None]]] = []

    def now_ms(self) -> float:
        return self._ms

    def advance(self, ms: float) -> None:
        self._ms += ms
        remaining: list[tuple[float, asyncio.Future[None]]] = []
        for target, fut in self._waiters:
            if not fut.done() and target <= self._ms:
                fut.set_result(None)
            elif not fut.done():
                remaining.append((target, fut))
        self._waiters = remaining

    async def sleep(self, ms: float) -> None:
        if ms <= 0:
            return
        fut: asyncio.Future[None] = asyncio.get_event_loop().create_future()
        self._waiters.append((self._ms + ms, fut))
        await fut
