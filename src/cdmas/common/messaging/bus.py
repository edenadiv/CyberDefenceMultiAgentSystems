"""Asynchronous publish-subscribe bus (SDD §3.1).

Abstract ``MessageBus`` with an ``InMemoryBus`` implementation for tests and
single-process runs. Guarantees per-topic FIFO delivery, idempotent dedup on
(sender, seq), Lamport total ordering, and deadline-bounded receives. The Kafka
implementation (KafkaBus) is added in Phase 4 behind the same interface.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict

from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.lamport import LamportClock
from cdmas.common.messaging.topics import Topic


class Subscription:
    """A per-(topic, agent) inbox backed by an asyncio queue."""

    def __init__(self, topic: Topic, agent_id: str, queue: asyncio.Queue[ACLMessage]) -> None:
        self.topic = topic
        self.agent_id = agent_id
        self._queue = queue

    async def get(self, timeout: float | None = None) -> ACLMessage | None:
        """Return the next message, or None if `timeout` seconds elapse."""
        if timeout is None:
            return await self._queue.get()
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def get_nowait(self) -> ACLMessage | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def __aiter__(self) -> Subscription:
        return self

    async def __anext__(self) -> ACLMessage:
        return await self._queue.get()


class MessageBus(ABC):
    @abstractmethod
    async def publish(self, message: ACLMessage) -> None: ...

    @abstractmethod
    def subscribe(self, topic: Topic, agent_id: str) -> Subscription: ...

    async def start(self) -> None:  # pragma: no cover - no-op for in-memory
        return None

    async def stop(self) -> None:  # pragma: no cover - no-op for in-memory
        return None


class InMemoryBus(MessageBus):
    def __init__(self) -> None:
        self._subs: dict[Topic, dict[str, asyncio.Queue[ACLMessage]]] = defaultdict(dict)
        self._seen: dict[str, int] = {}  # sender -> highest seq delivered (dedup)
        self._clock = LamportClock()
        self._lock = asyncio.Lock()

    def subscribe(self, topic: Topic, agent_id: str) -> Subscription:
        queue: asyncio.Queue[ACLMessage] = asyncio.Queue()
        self._subs[topic][agent_id] = queue
        return Subscription(topic, agent_id, queue)

    async def publish(self, message: ACLMessage) -> None:
        async with self._lock:
            # Idempotent dedup on (sender, seq); seq==0 means "unsequenced".
            if message.seq:
                if message.seq <= self._seen.get(message.sender, 0):
                    return
                self._seen[message.sender] = message.seq
            # Authoritative total-order stamp.
            message.lamport_ts = self._clock.tick()
            for agent_id, queue in self._subs.get(message.topic, {}).items():
                if agent_id == message.sender:
                    continue  # never echo to sender
                if message.receiver not in ("BROADCAST", agent_id):
                    continue  # targeted message for someone else
                queue.put_nowait(message)
