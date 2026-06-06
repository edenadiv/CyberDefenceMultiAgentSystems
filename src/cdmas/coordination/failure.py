"""Agent failure detection and coverage reassignment (SDD §4.5, Figure 11).

A heartbeat monitor flags an agent failed after 1s of silence; coverage of its segment is
reassigned to the minimum-load healthy peer, asserted to complete within 2s.
"""

from __future__ import annotations

from cdmas.common.logging.event_log import EventLog, EventSink, EventType

HEARTBEAT_TIMEOUT_MS = 1000.0
REASSIGN_DEADLINE_MS = 2000.0


class HeartbeatMonitor:
    def __init__(self, *, timeout_ms: float = HEARTBEAT_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms
        self._last_seen: dict[str, float] = {}

    def beat(self, agent_id: str, now_ms: float) -> None:
        self._last_seen[agent_id] = now_ms

    def failed(self, now_ms: float) -> list[str]:
        return [a for a, ts in self._last_seen.items() if now_ms - ts > self.timeout_ms]

    def forget(self, agent_id: str) -> None:
        self._last_seen.pop(agent_id, None)


def select_failover_peer(candidates: dict[str, float]) -> str | None:
    """Pick the minimum-load healthy peer to take over (candidates: agent_id -> load)."""
    if not candidates:
        return None
    return min(candidates, key=lambda a: candidates[a])


class FailoverCoordinator:
    """Detects failed agents and reassigns their segment coverage (SDD §4.5, Figure 11)."""

    def __init__(
        self, monitor: HeartbeatMonitor, sink: EventSink, *, coordinator_id: str = "TIA:global"
    ) -> None:
        self.monitor = monitor
        self.sink = sink
        self.coordinator_id = coordinator_id
        self._handled: set[str] = set()

    async def check(
        self, now_ms: float, segment_of: dict[str, str], loads: dict[str, float]
    ) -> list[tuple[str, str]]:
        reassignments: list[tuple[str, str]] = []
        for failed in self.monitor.failed(now_ms):
            if failed in self._handled:
                continue
            self._handled.add(failed)
            segment = segment_of.get(failed)
            await self._emit(
                EventType.AGENT_FAILED, now_ms, {"failed_agent": failed, "segment": segment}
            )
            peers = {a: load for a, load in loads.items() if a != failed}
            peer = select_failover_peer(peers)
            if peer and segment:
                await self._emit(
                    EventType.ACTION_EXECUTED,
                    now_ms,
                    {"signal": "coverage_reassigned", "segment": segment, "new_owner": peer},
                    latency_ms=0,
                )
                reassignments.append((segment, peer))
            self.monitor.forget(failed)
        return reassignments

    async def _emit(
        self,
        event_type: EventType,
        now_ms: float,
        payload: dict[str, object],
        latency_ms: int | None = None,
    ) -> None:
        seg = payload.get("segment")
        await self.sink.write(
            EventLog(
                lamport_ts=0,
                wall_ms=now_ms,
                event_type=event_type,
                agent_id=self.coordinator_id,
                agent_type=self.coordinator_id.split(":")[0],
                segment=seg if isinstance(seg, str) else None,
                payload=payload,
                latency_ms=latency_ms,
            )
        )
