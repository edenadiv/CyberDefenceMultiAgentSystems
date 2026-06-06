from cdmas.agents._common.features import build_training_set, extract_features
from cdmas.agents.aca.classifier import HybridClassifier
from cdmas.common.models.enums import AttackType, Classification, Segment
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.traffic import TrafficGenerator


def _fitted() -> HybridClassifier:
    clf = HybridClassifier()
    x, y = build_training_set(seed=0, samples_per_class=30, segment=Segment.PUBLIC_FACING)
    clf.fit(x, y)
    return clf


def test_classifies_ddos_as_confirmed_threat():
    clf = _fitted()
    gen = TrafficGenerator(seed=99)
    inj = AttackInjector(seed=99)
    inj.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    pkts = gen.sample(Segment.PUBLIC_FACING, 50) + inj.overlay(Segment.PUBLIC_FACING, 0)
    v = clf.predict(extract_features(pkts))
    assert v.classification is Classification.CONFIRMED_THREAT
    assert v.attack_type is AttackType.DDOS
    assert 0.0 <= v.severity <= 1.0 and v.severity > 0.7


def test_classifies_normal_as_normal():
    clf = _fitted()
    gen = TrafficGenerator(seed=123)
    v = clf.predict(extract_features(gen.sample(Segment.PUBLIC_FACING, 50)))
    assert v.classification is Classification.NORMAL


def test_zero_day_flagged_as_suspicious_novel():
    clf = _fitted()
    gen = TrafficGenerator(seed=7)
    inj = AttackInjector(seed=7)
    inj.inject(AttackSpec(type=AttackType.ZERO_DAY, segment=Segment.PUBLIC_FACING))
    pkts = gen.sample(Segment.PUBLIC_FACING, 50) + inj.overlay(Segment.PUBLIC_FACING, 0)
    v = clf.predict(extract_features(pkts))
    assert v.classification is Classification.SUSPICIOUS
    assert v.attack_type is AttackType.NOVEL


def test_partial_update_returns_delta():
    clf = _fitted()
    gen = TrafficGenerator(seed=3)
    feats = extract_features(gen.sample(Segment.PUBLIC_FACING, 50))
    delta = clf.partial_update(feats, "NORMAL")
    assert isinstance(delta, float)
