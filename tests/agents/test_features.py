from cdmas.agents._common.features import (
    NUM_FEATURES,
    TRAIN_LABELS,
    build_training_set,
    extract_features,
)
from cdmas.common.models.enums import AttackType, Segment
from cdmas.simulator.attacks import AttackInjector, AttackSpec
from cdmas.simulator.traffic import TrafficGenerator


def test_extract_features_shape_and_empty():
    assert extract_features([]) == [0.0] * NUM_FEATURES
    gen = TrafficGenerator(seed=0)
    feats = extract_features(gen.sample(Segment.SERVER, 20))
    assert len(feats) == NUM_FEATURES
    assert feats[0] > 0  # volume


def test_ddos_features_differ_from_normal():
    gen = TrafficGenerator(seed=0)
    base = gen.sample(Segment.PUBLIC_FACING, 50)
    inj = AttackInjector(seed=5)
    inj.inject(AttackSpec(type=AttackType.DDOS, segment=Segment.PUBLIC_FACING, intensity=2.0))
    attacked = extract_features(base + inj.overlay(Segment.PUBLIC_FACING, 0))
    normal = extract_features(base)
    assert attacked[0] > normal[0] * 2  # volume much higher
    assert attacked[3] > normal[3]  # more unique src IPs


def test_training_set_has_all_labels():
    x, y = build_training_set(seed=0, samples_per_class=5)
    assert len(x) == len(y) == 5 * len(TRAIN_LABELS)
    assert set(y) == set(TRAIN_LABELS)
    assert all(len(row) == NUM_FEATURES for row in x)
