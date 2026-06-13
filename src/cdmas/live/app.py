"""FastAPI surface for the live MAS: a WebSocket event stream plus manual-action and
run-control endpoints. Additive — separate from the simulator's ``create_app``."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cdmas.live.session import LiveSession
from cdmas.simulator.auth import token_ok

_log = logging.getLogger("cdmas.live")
DEFAULT_TOKEN = "changeme"


class ManualDos(BaseModel):
    segment: str
    intensity: float = 3.0


class ManualLegal(BaseModel):
    segment: str
    volume: float = 1.0


class ModeReq(BaseModel):
    mode: str


def create_live_app(
    session: LiveSession,
    *,
    token: str = DEFAULT_TOKEN,
    allow_origins: list[str] | None = None,
    autostart: bool = True,
) -> FastAPI:
    if token == DEFAULT_TOKEN:
        _log.warning(
            "live server is using the DEFAULT API token; set CDMAS_SIM_API_TOKEN before production"
        )
    run_task: dict[str, asyncio.Task[None] | None] = {"task": None}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if autostart:
            run_task["task"] = asyncio.create_task(session.run())
        try:
            yield
        finally:
            session.stop()
            task = run_task["task"]
            if task is not None:
                task.cancel()

    app = FastAPI(title="CDMAS Live", lifespan=lifespan)
    # The dashboard runs on a different origin (Vite dev server); allow it to call us.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def auth(authorization: str | None = Header(default=None)) -> None:
        if not token_ok(authorization, token):
            raise HTTPException(status_code=401, detail="invalid token")

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        # Unauthenticated liveness/readiness probe for orchestrators / load balancers.
        return {"status": "ok", "round": session._round, "subscribers": session.hub.subscribers}

    @app.get("/live/topology")
    def topology(_: None = Depends(auth)) -> dict[str, Any]:
        return session.topology()

    @app.post("/manual/send-dos")
    def send_dos(req: ManualDos, _: None = Depends(auth)) -> dict[str, Any]:
        session.send_dos(req.segment, req.intensity)
        return {"status": "ok", "signal": "manual_dos", "segment": req.segment}

    @app.post("/manual/send-legal")
    def send_legal(req: ManualLegal, _: None = Depends(auth)) -> dict[str, Any]:
        session.send_legal(req.segment, req.volume)
        return {"status": "ok", "signal": "manual_legal", "segment": req.segment}

    @app.post("/control/mode")
    def control_mode(req: ModeReq, _: None = Depends(auth)) -> dict[str, Any]:
        session.set_mode(req.mode)
        return {"status": "ok", "mode": session.mode}

    @app.post("/control/next")
    def control_next(_: None = Depends(auth)) -> dict[str, Any]:
        session.request_next()
        return {"status": "ok"}

    @app.websocket("/ws/events")
    async def ws_events(ws: WebSocket) -> None:
        if token and ws.query_params.get("token") != token:
            await ws.close(code=1008)
            return
        await ws.accept()
        await ws.send_json(
            {
                "kind": "topology",
                "server_seq": 0,
                "ts_ms": session.clock.now_ms(),
                "payload": session.topology(),
            }
        )
        queue = session.hub.subscribe()
        session.emit_status()  # immediate snapshot so the UI never shows ambiguous status
        try:
            while True:
                frame = await queue.get()
                await ws.send_json(frame.model_dump(mode="json"))
        except WebSocketDisconnect:
            return
        finally:
            session.hub.unsubscribe(queue)

    return app
