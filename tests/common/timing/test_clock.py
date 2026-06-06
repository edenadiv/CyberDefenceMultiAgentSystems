import asyncio

from cdmas.common.timing.clock import ManualClock, WallClock


def test_wall_clock_is_monotonic():
    c = WallClock()
    assert c.now_ms() <= c.now_ms()


def test_manual_clock_now_and_advance():
    c = ManualClock()
    assert c.now_ms() == 0
    c.advance(250)
    assert c.now_ms() == 250


async def test_manual_clock_sleep_blocks_until_advance():
    clk = ManualClock()
    done = asyncio.Event()

    async def sleeper() -> None:
        await clk.sleep(100)
        done.set()

    task = asyncio.create_task(sleeper())
    await asyncio.sleep(0)  # let the sleeper register its waiter
    assert not done.is_set()

    clk.advance(50)
    await asyncio.sleep(0)
    assert not done.is_set()  # 50 < 100, still blocked

    clk.advance(50)
    await asyncio.sleep(0)
    assert done.is_set()  # reached 100ms
    await task
    assert clk.now_ms() == 100


async def test_manual_clock_zero_sleep_returns_immediately():
    clk = ManualClock()
    await clk.sleep(0)  # must not block
