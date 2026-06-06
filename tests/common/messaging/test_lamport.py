from cdmas.common.messaging.lamport import LamportClock


def test_tick_monotonic():
    c = LamportClock()
    assert c.tick() == 1
    assert c.tick() == 2
    assert c.time == 2


def test_update_takes_max_plus_one():
    c = LamportClock()
    c.tick()  # 1
    assert c.update(5) == 6   # max(1,5)+1
    assert c.update(2) == 7   # max(6,2)+1
