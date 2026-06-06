from cdmas.agents._common.features import build_training_set, extract_features
from cdmas.agents.aca.agent import AnomalyClassifierAgent
from cdmas.agents.aca.classifier import HybridClassifier
from cdmas.common.logging.event_log import EventType
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import AttackType, Performative, Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.traffic import TrafficGenerator


def _ddos_features() -> list[float]:
    gen = TrafficGenerator(seed=50)
    inj = AttackInjector(seed=50)
    inj.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    pkts = gen.sample(Segment.PUBLIC_FACING, 50) + inj.overlay(Segment.PUBLIC_FACING, 0)
    return extract_features(pkts)


def _shared_classifier() -> HybridClassifier:
    clf = HybridClassifier()
    x, y = build_training_set(seed=0, samples_per_class=20, segment=Segment.PUBLIC_FACING)
    clf.fit(x, y)
    return clf


async def test_aca_classifies_alert_and_publishes_report():
    clk = ManualClock()
    bus = InMemoryBus()
    reports = bus.subscribe(Topic.THREAT_REPORTS, "OBSERVER")
    aca = AnomalyClassifierAgent(
        "ACA:seg1", "public-facing", bus, clock=clk, classifier=_shared_classifier()
    )
    aca.setup()

    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="TMA:seg1",
            receiver="BROADCAST",
            topic=Topic.ALERTS,
            seq=1,
            content={"alert": {"alert_id": "a1"}, "features": _ddos_features(), "ts_ms": 0.0},
        )
    )
    clk.advance(10)
    await aca.step()

    msg = await reports.get(timeout=0.05)
    assert msg is not None
    assert msg.content["threat"]["classification"] == "CONFIRMED_THREAT"

    classified = [e for e in aca.sink.events if e.event_type is EventType.THREAT_CLASSIFIED]
    assert classified and classified[-1].latency_ms is not None and classified[-1].latency_ms < 200


async def test_aca_online_learning_on_resolution():
    clk = ManualClock()
    bus = InMemoryBus()
    aca = AnomalyClassifierAgent(
        "ACA:seg1", "public-facing", bus, clock=clk, classifier=_shared_classifier()
    )
    aca.setup()
    # Classify one alert so there is a recent example to learn from.
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="TMA:seg1",
            receiver="BROADCAST",
            topic=Topic.ALERTS,
            seq=1,
            content={"alert": {"alert_id": "a1"}, "features": _ddos_features(), "ts_ms": 0.0},
        )
    )
    await aca.step()
    # Now a resolution arrives -> triggers online learning.
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="RCA:seg1",
            receiver="BROADCAST",
            topic=Topic.RESOLUTION,
            seq=1,
            content={"threat_id": "t1"},
        )
    )
    await aca.step()
    updates = [
        e
        for e in aca.sink.events
        if e.event_type is EventType.ACTION_EXECUTED and e.payload.get("signal") == "online_update"
    ]
    assert updates
