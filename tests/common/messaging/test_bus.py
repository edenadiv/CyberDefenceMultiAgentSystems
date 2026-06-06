from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


def _msg(sender: str, seq: int, receiver: str = "BROADCAST") -> ACLMessage:
    return ACLMessage(
        performative=Performative.INFORM,
        sender=sender,
        receiver=receiver,
        topic=Topic.ALERTS,
        seq=seq,
        content={"n": seq},
    )


async def test_fifo_delivery_and_lamport_stamp():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1))
    await bus.publish(_msg("TMA:seg1", 2))
    m1 = await sub.get(timeout=1)
    m2 = await sub.get(timeout=1)
    assert (m1.content["n"], m2.content["n"]) == (1, 2)  # FIFO
    assert m1.lamport_ts < m2.lamport_ts                  # bus-stamped total order


async def test_idempotent_dedup():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1))
    await bus.publish(_msg("TMA:seg1", 1))  # duplicate seq -> dropped
    assert (await sub.get(timeout=0.1)).content["n"] == 1
    assert await sub.get(timeout=0.1) is None  # nothing more


async def test_no_self_echo_and_targeted_receiver():
    bus = InMemoryBus()
    tma = bus.subscribe(Topic.ALERTS, "TMA:seg1")
    aca = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    await bus.publish(_msg("TMA:seg1", 1, receiver="ACA:seg1"))
    assert (await aca.get(timeout=0.1)).content["n"] == 1
    assert await tma.get(timeout=0.1) is None  # sender does not receive own msg


async def test_deadline_returns_none_when_idle():
    bus = InMemoryBus()
    sub = bus.subscribe(Topic.ALERTS, "ACA:seg1")
    assert await sub.get(timeout=0.05) is None
