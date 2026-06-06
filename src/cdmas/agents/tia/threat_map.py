"""Global threat map: cross-segment aggregation, correlation, ranking (SDD §2.5)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cdmas.common.models.enums import Segment

_CORRELATION_WINDOW_MS = 2000.0


@dataclass
class ThreatEntry:
    threat_id: str
    segment: Segment
    severity: float
    ts_ms: float
    attack_type: str


class GlobalThreatMap:
    def __init__(self) -> None:
        self._by_segment: dict[Segment, list[ThreatEntry]] = defaultdict(list)

    def add(self, entry: ThreatEntry) -> None:
        self._by_segment[entry.segment].append(entry)

    def active_segments(
        self, now_ms: float, window_ms: float = _CORRELATION_WINDOW_MS
    ) -> set[Segment]:
        return {
            seg
            for seg, entries in self._by_segment.items()
            if any(now_ms - e.ts_ms <= window_ms for e in entries)
        }

    def priority_list(self, top: int = 10) -> list[ThreatEntry]:
        everything = [e for entries in self._by_segment.values() for e in entries]
        return sorted(everything, key=lambda e: e.severity, reverse=True)[:top]
