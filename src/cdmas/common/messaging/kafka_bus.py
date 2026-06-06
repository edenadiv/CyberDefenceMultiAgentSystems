"""Kafka-backed message bus (SDD §3.1, §5.1).

Implements the same ``MessageBus`` ABC as ``InMemoryBus`` so agents are bus-agnostic. Each
subscription is its own Kafka consumer group, so every subscriber receives every message
(pub/sub fan-out, not load-balancing). Lamport stamping on publish, idempotent dedup on
(sender, seq), and the same receiver/self-echo routing rules as the in-memory bus.
"""

from __future__ import annotations

import asyncio

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from cdmas.common.messaging.acl import ACLMessage, parse_message
from cdmas.common.messaging.bus import MessageBus, Subscription
from cdmas.common.messaging.lamport import LamportClock
from cdmas.common.messaging.topics import Topic


class KafkaBus(MessageBus):
    def __init__(
        self, bootstrap_servers: str, *, client_id: str = "cdmas", topic_prefix: str = "cdmas."
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._client_id = client_id
        self._prefix = topic_prefix
        self._producer: AIOKafkaProducer | None = None
        self._pending_subs: list[tuple[Topic, str, asyncio.Queue[ACLMessage]]] = []
        self._consumers: list[AIOKafkaConsumer] = []
        self._tasks: list[asyncio.Task[None]] = []
        self._clock = LamportClock()
        self._seen: dict[str, int] = {}

    def _kafka_topic(self, topic: Topic) -> str:
        return f"{self._prefix}{topic.value}"

    def subscribe(self, topic: Topic, agent_id: str) -> Subscription:
        queue: asyncio.Queue[ACLMessage] = asyncio.Queue()
        self._pending_subs.append((topic, agent_id, queue))
        return Subscription(topic, agent_id, queue)

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap, client_id=self._client_id
        )
        await self._producer.start()
        for topic, agent_id, queue in self._pending_subs:
            consumer = AIOKafkaConsumer(
                self._kafka_topic(topic),
                bootstrap_servers=self._bootstrap,
                group_id=f"{self._client_id}.{agent_id}.{topic.value}",
                auto_offset_reset="latest",
                enable_auto_commit=True,
            )
            await consumer.start()
            self._consumers.append(consumer)
            self._tasks.append(asyncio.create_task(self._consume(consumer, agent_id, queue)))

    async def publish(self, message: ACLMessage) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaBus.start() must be called before publish()")
        message.lamport_ts = self._clock.tick()
        await self._producer.send_and_wait(
            self._kafka_topic(message.topic), message.model_dump_json().encode()
        )

    async def _consume(
        self, consumer: AIOKafkaConsumer, agent_id: str, queue: asyncio.Queue[ACLMessage]
    ) -> None:
        async for record in consumer:
            try:
                message = parse_message(record.value)
            except Exception:
                continue
            if message.sender == agent_id:
                continue
            if message.receiver not in ("BROADCAST", agent_id):
                continue
            if message.seq and message.seq <= self._seen.get(message.sender, 0):
                continue
            if message.seq:
                self._seen[message.sender] = message.seq
            self._clock.update(message.lamport_ts)
            await queue.put(message)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for consumer in self._consumers:
            await consumer.stop()
        if self._producer is not None:
            await self._producer.stop()
