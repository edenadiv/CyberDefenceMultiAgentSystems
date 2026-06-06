"""Agent factory — builds the full defense fleet for a set of segments.

The Phase 8 validator harness binds to ``build_all``; the production runner uses it too.
Per segment: TMA + ACA + RCA. Global: TIA + RAA.
"""

from __future__ import annotations

from cdmas.agents.aca.agent import AnomalyClassifierAgent
from cdmas.agents.raa.agent import ResourceAllocatorAgent
from cdmas.agents.rca.agent import ResponseCoordinatorAgent
from cdmas.agents.tia.agent import ThreatIntelligenceAgent
from cdmas.agents.tma.agent import TrafficMonitorAgent
from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.logging.event_log import EventSink
from cdmas.common.messaging.bus import MessageBus
from cdmas.common.models.enums import Segment
from cdmas.common.timing.clock import Clock
from cdmas.simulator.client import SimClientProtocol


def build_all(
    segments: list[Segment],
    bus: MessageBus,
    sim: SimClientProtocol,
    sink: EventSink,
    clock: Clock,
) -> list[BaseAgent]:
    agents: list[BaseAgent] = []
    for seg in segments:
        sid = seg.value
        agents.append(TrafficMonitorAgent(f"TMA:{sid}", sid, bus, sim, sink, clock=clock))
        agents.append(AnomalyClassifierAgent(f"ACA:{sid}", sid, bus, sink, clock=clock))
        agents.append(ResponseCoordinatorAgent(f"RCA:{sid}", sid, bus, sim, sink, clock=clock))
    agents.append(ThreatIntelligenceAgent("TIA:global", None, bus, sink, clock=clock))
    agents.append(ResourceAllocatorAgent("RAA:global", None, bus, sim, sink, clock=clock))
    return agents
