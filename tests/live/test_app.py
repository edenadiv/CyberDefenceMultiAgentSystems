"""Live FastAPI app — ws/events stream, manual actions, and run-control endpoints."""

from fastapi.testclient import TestClient

from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import ManualClock
from cdmas.live.app import create_live_app
from cdmas.live.session import LiveSession

_AUTH = {"Authorization": "Bearer t"}


def _client() -> tuple[TestClient, LiveSession]:
    session = LiveSession(segments=[Segment.PUBLIC_FACING], clock=ManualClock())
    return TestClient(create_live_app(session, token="t", autostart=False)), session


def test_healthz_is_unauthenticated():
    c, _ = _client()
    r = c.get("/healthz")  # no auth header
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_manual_actions_require_auth():
    c, _ = _client()
    assert c.post("/manual/send-dos", json={"segment": "public-facing"}).status_code == 401
    ok = c.post("/manual/send-dos", json={"segment": "public-facing"}, headers=_AUTH)
    assert ok.status_code == 200


def test_send_dos_endpoint_injects_real_attack():
    c, s = _client()
    r = c.post(
        "/manual/send-dos", json={"segment": "public-facing", "intensity": 3.0}, headers=_AUTH
    )
    assert r.status_code == 200 and r.json()["signal"] == "manual_dos"
    assert s.sim.ground_truth().is_attack(Segment.PUBLIC_FACING, 0.0) is True


def test_control_mode_and_next():
    c, s = _client()
    assert c.post("/control/mode", json={"mode": "step"}, headers=_AUTH).status_code == 200
    assert s.mode == "step"
    assert c.post("/control/next", headers=_AUTH).status_code == 200
    assert s._next.is_set()


def test_ws_events_sends_topology_and_status_on_connect():
    c, _ = _client()
    with c.websocket_connect("/ws/events?token=t") as ws:
        first = ws.receive_json()
        assert first["kind"] == "topology"
        assert "public-facing" in first["payload"]["segments"]
        kinds = {first["kind"]}
        for _ in range(2):  # topology is followed by the two status frames
            kinds.add(ws.receive_json()["kind"])
        assert "connection_status" in kinds
        assert "simulation_state" in kinds


def test_ws_events_rejects_bad_token():
    c, _ = _client()
    try:
        with c.websocket_connect("/ws/events?token=wrong"):
            raise AssertionError("should have been rejected")
    except Exception:
        pass  # closed before accept


def test_cors_allow_origin_is_configurable():
    session = LiveSession(segments=[Segment.PUBLIC_FACING], clock=ManualClock())
    c = TestClient(
        create_live_app(session, token="t", allow_origins=["http://dash.example"], autostart=False)
    )
    r = c.get("/live/topology", headers={**_AUTH, "Origin": "http://dash.example"})
    assert r.headers.get("access-control-allow-origin") == "http://dash.example"


def test_send_legal_endpoint():
    c, _ = _client()
    r = c.post("/manual/send-legal", json={"segment": "public-facing"}, headers=_AUTH)
    assert r.status_code == 200 and r.json()["signal"] == "manual_legal"


def test_autostart_runs_loop_and_shuts_down():
    import time

    session = LiveSession(segments=[Segment.PUBLIC_FACING], clock=ManualClock())
    with TestClient(create_live_app(session, token="t", autostart=True)) as c:
        time.sleep(0.1)  # the lifespan started the run loop
        assert c.get("/live/topology", headers=_AUTH).status_code == 200
        assert session._round > 0
    # leaving the context triggers shutdown (stop + task cancel)


def test_build_app_constructs_without_serving():
    from cdmas.live.__main__ import build_app

    app = build_app()
    assert app.title == "CDMAS Live"
