"""Production agent bootstrap: wire Settings -> KafkaBus + SimClient -> run the agent."""

from __future__ import annotations

import asyncio

from cdmas.agents.aca.agent import AnomalyClassifierAgent
from cdmas.agents.raa.agent import ResourceAllocatorAgent
from cdmas.agents.rca.agent import ResponseCoordinatorAgent
from cdmas.agents.tia.agent import ThreatIntelligenceAgent
from cdmas.agents.tma.agent import TrafficMonitorAgent
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.config import get_settings
from cdmas.common.logging.event_log import StructlogSink
from cdmas.common.messaging.kafka_bus import KafkaBus
from cdmas.common.timing.clock import WallClock
from cdmas.simulator.client import SimClient


def _build(
    kind: str,
    agent_id: str,
    segment: str | None,
    bus: KafkaBus,
    sim: SimClient,
    sink: StructlogSink,
    clock: WallClock,
) -> BaseAgent:
    if kind == "TMA":
        return TrafficMonitorAgent(agent_id, segment, bus, sim, sink, clock=clock)
    if kind == "ACA":
        return AnomalyClassifierAgent(agent_id, segment, bus, sink, clock=clock)
    if kind == "RCA":
        return ResponseCoordinatorAgent(agent_id, segment, bus, sim, sink, clock=clock)
    if kind == "TIA":
        return ThreatIntelligenceAgent(agent_id, segment, bus, sink, clock=clock)
    if kind == "RAA":
        return ResourceAllocatorAgent(agent_id, segment, bus, sim, sink, clock=clock)
    raise ValueError(f"unknown agent kind: {kind}")


async def _run(kind: str) -> None:
    settings = get_settings()
    agent_id = settings.agent_id or f"{kind}:default"
    bus = KafkaBus(settings.kafka_bootstrap, client_id=settings.kafka_client_id)
    sim = SimClient(settings.sim_base_url, settings.sim_api_token, agent_id=agent_id)
    agent = _build(kind, agent_id, settings.agent_segment, bus, sim, StructlogSink(), WallClock())
    await bus.start()
    try:
        await agent.run()
    finally:
        await bus.stop()


def run_agent(kind: str) -> None:
    asyncio.run(_run(kind))
