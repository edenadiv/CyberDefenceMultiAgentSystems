"""LiveSession — runs the real fleet in-process and streams it to the EventHub."""

import asyncio

from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.live.hub import StreamFrame
from cdmas.live.session import LiveSession


def _drain(q) -> list[StreamFrame]:
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def _session() -> LiveSession:
    return LiveSession(segments=[Segment.PUBLIC_FACING], clock=ManualClock())


async def _wait_until(predicate, timeout: float = 3.0) -> bool:
    """Poll a condition rather than sleeping a fixed time — robust under CI load."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.005)
    return False


async def test_send_dos_injects_attack_and_emits_sim_event():
    s = _session()
    q = s.hub.subscribe()
    s.send_dos("public-facing", intensity=3.0)
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, s.clock.now_ms()) is True
    sim_events = [f for f in _drain(q) if f.kind == "sim_event"]
    assert any(f.payload.get("signal") == "manual_dos" for f in sim_events)


async def test_manual_dos_expires_so_the_system_can_recover():
    s = _session()
    s.send_dos("public-facing", duration_ms=200)
    gt = s.sim.ground_truth()
    now = s.clock.now_ms()
    assert gt.is_attack(Segment.PUBLIC_FACING, now) is True  # active now
    assert gt.is_attack(Segment.PUBLIC_FACING, now + 500) is False  # subsided later


async def test_send_legal_does_not_inject_an_attack():
    s = _session()
    q = s.hub.subscribe()
    s.send_legal("public-facing")
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, s.clock.now_ms()) is False
    sim_events = [f for f in _drain(q) if f.kind == "sim_event"]
    assert any(f.payload.get("signal") == "manual_legal" for f in sim_events)


async def test_live_fleet_detects_injected_dos():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):  # warm up the traffic baseline
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(15):
        await s.tick_round()
    agent_events = [f for f in _drain(q) if f.kind == "agent_event"]
    types = {f.payload["event_type"] for f in agent_events}
    assert "ALERT_PUBLISHED" in types  # the real TMA detected the live attack


async def test_finer_clock_yields_nonzero_latencies():
    s = _session()
    q = s.hub.subscribe()
    for _ in range(30):
        await s.tick_round()
    s.send_dos("public-facing", intensity=4.0)
    for _ in range(15):
        await s.tick_round()
    agent_events = [f for f in _drain(q) if f.kind == "agent_event"]
    lats = [
        f.payload.get("latency_ms") for f in agent_events if f.payload.get("latency_ms") is not None
    ]
    # sub-stepping spreads the pipeline in time, so decisions take a real (>0) latency
    assert any((latency or 0) > 0 for latency in lats)


async def test_status_frames_report_topology_and_stream():
    s = _session()
    q = s.hub.subscribe()
    await s.tick_round()
    frames = _drain(q)
    status = [f for f in frames if f.kind == "connection_status"]
    state = [f for f in frames if f.kind == "simulation_state"]
    assert status and state
    assert status[-1].payload["stream_connected"] is True
    assert status[-1].payload["agents_total"] >= 1
    assert state[-1].payload["mode"] == "auto"


async def test_step_mode_gate_can_be_released():
    s = _session()
    s.set_mode("step")
    assert s.mode == "step"
    s.request_next()  # arms the gate
    assert s._next.is_set()


async def test_run_loop_auto_advances_then_stops():
    s = _session()
    task = asyncio.create_task(s.run(interval_s=0.001))
    assert await _wait_until(lambda: s._round > 0)  # auto mode advances on its own
    s.stop()
    await asyncio.wait_for(task, timeout=2.0)


async def test_run_loop_step_gate_holds_until_next():
    s = _session()
    s.set_mode("step")
    task = asyncio.create_task(s.run(interval_s=0.001))
    # In step mode the loop gates before the first tick, so it never advances on its own.
    await asyncio.sleep(0.05)
    assert s._round == 0
    s.request_next()
    assert await _wait_until(lambda: s._round >= 1)  # advances once Next is requested
    s.stop()
    await asyncio.wait_for(task, timeout=2.0)
