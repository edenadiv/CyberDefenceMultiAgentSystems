from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.clock import SimClock


def test_realtime_speed():
    base = ManualClock()
    sc = SimClock(base, speed=1.0)
    base.advance(40)
    assert sc.sim_now_ms() == 40


def test_accelerated_speed():
    base = ManualClock()
    sc = SimClock(base, speed=10.0, tick_ms=10)
    assert sc.sim_now_ms() == 0
    base.advance(10)
    assert sc.sim_now_ms() == 100  # 10ms wall × 10 = 100ms sim


def test_slow_motion_speed():
    base = ManualClock()
    sc = SimClock(base, speed=0.5)
    base.advance(100)
    assert sc.sim_now_ms() == 50
