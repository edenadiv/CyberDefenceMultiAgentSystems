from cdmas.agents.tma.baseline import RollingBaseline


def test_warmup_suppresses_deviation():
    b = RollingBaseline(warmup=5)
    for _ in range(3):
        b.update(100.0)
    assert b.deviation(100_000.0) == 0.0  # still warming up


def test_deviation_after_warmup():
    b = RollingBaseline(warmup=5)
    for v in [100.0, 102.0, 98.0, 101.0, 99.0, 100.0]:
        b.update(v)
    assert abs(b.mean - 100.0) < 1.0
    assert b.deviation(100.0) < 1.0  # in-band
    assert b.deviation(10_000.0) > 2.0  # spike detected


def test_window_evicts_old_values():
    b = RollingBaseline(window=3, warmup=1)
    for v in [1.0, 2.0, 3.0, 4.0]:
        b.update(v)
    assert abs(b.mean - 3.0) < 1e-9  # only last 3 kept (2,3,4)
