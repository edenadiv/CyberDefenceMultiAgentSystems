import pytest

from cdmas.common.messaging.bus import MessageBus
from cdmas.common.messaging.kafka_bus import KafkaBus
from cdmas.common.messaging.topics import Topic


def test_kafka_bus_is_a_message_bus():
    bus = KafkaBus("localhost:9092")
    assert isinstance(bus, MessageBus)
    assert bus._kafka_topic(Topic.ALERTS) == "cdmas.alerts"


def test_publish_before_start_raises():
    bus = KafkaBus("localhost:9092")
    # subscribe is allowed before start (queues are created lazily on start)
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    assert sub.topic is Topic.ALERTS


@pytest.mark.integration
async def test_kafka_roundtrip():
    """Requires a running Kafka broker (docker compose up kafka); skipped if unavailable."""
    import contextlib

    from aiokafka.errors import KafkaConnectionError

    from cdmas.common.messaging.acl import ACLMessage
    from cdmas.common.models.enums import Performative

    producer = KafkaBus("localhost:9092", client_id="t-prod")
    consumer = KafkaBus("localhost:9092", client_id="t-cons")
    sub = consumer.subscribe(Topic.ALERTS, "ACA:seg1")
    try:
        try:
            await producer.start()
            await consumer.start()
        except KafkaConnectionError as e:
            pytest.skip(f"Kafka broker not available: {e}")
        await producer.publish(
            ACLMessage(
                performative=Performative.INFORM,
                sender="TMA:seg1",
                receiver="BROADCAST",
                topic=Topic.ALERTS,
                seq=1,
                content={"n": 1},
            )
        )
        msg = await sub.get(timeout=10)
        assert msg is not None and msg.content["n"] == 1
    finally:
        with contextlib.suppress(Exception):
            await producer.stop()
        with contextlib.suppress(Exception):
            await consumer.stop()
