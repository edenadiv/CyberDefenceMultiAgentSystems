"""`python -m cdmas.live` — serve the live single-process MAS demo with uvicorn.

Config (CDMAS_* env): ``CDMAS_LIVE_PORT`` (default: simulator port),
``CDMAS_LIVE_CORS_ORIGINS`` (comma-separated; ``*`` for any), ``CDMAS_SIM_API_TOKEN``.
The dashboard's Live mode connects to ``ws://<host>:<port>/ws/events?token=<token>``.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from cdmas.common.config import get_settings
from cdmas.common.models.enums import Segment
from cdmas.live.app import create_live_app
from cdmas.live.session import LiveSession


def build_app() -> FastAPI:
    settings = get_settings()
    session = LiveSession(segments=list(Segment))
    origins = [o.strip() for o in settings.live_cors_origins.split(",") if o.strip()]
    return create_live_app(session, token=settings.sim_api_token, allow_origins=origins)


def main() -> None:
    settings = get_settings()
    port = settings.live_port or settings.sim_port
    uvicorn.run(build_app(), host=settings.sim_host, port=port)


if __name__ == "__main__":
    main()
