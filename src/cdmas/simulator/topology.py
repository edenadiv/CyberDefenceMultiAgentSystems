"""Four-segment network topology with lateral-movement adjacency (SDD §6.1.1)."""

from __future__ import annotations

from cdmas.common.models.enums import Segment

# Fixed default adjacency. Lateral movement is only possible along these edges; the
# security-monitoring zone observes all segments.
_DEFAULT_ADJACENCY: dict[Segment, set[Segment]] = {
    Segment.INTERNAL: {Segment.SERVER, Segment.SEC_MON},
    Segment.SERVER: {Segment.INTERNAL, Segment.PUBLIC_FACING, Segment.SEC_MON},
    Segment.PUBLIC_FACING: {Segment.SERVER, Segment.SEC_MON},
    Segment.SEC_MON: {Segment.INTERNAL, Segment.SERVER, Segment.PUBLIC_FACING},
}


class NetworkTopology:
    def __init__(self, segments: list[Segment] | None = None) -> None:
        self.segments = segments if segments is not None else list(Segment)
        active = set(self.segments)
        self._adj: dict[Segment, set[Segment]] = {
            s: {n for n in _DEFAULT_ADJACENCY.get(s, set()) if n in active} for s in self.segments
        }

    def neighbors(self, segment: Segment) -> set[Segment]:
        return self._adj.get(segment, set())

    def is_adjacent(self, a: Segment, b: Segment) -> bool:
        return b in self._adj.get(a, set())

    def adjacency_view(self) -> dict[str, list[str]]:
        return {s.value: sorted(n.value for n in adj) for s, adj in self._adj.items()}
