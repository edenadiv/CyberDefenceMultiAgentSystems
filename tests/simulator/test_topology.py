from cdmas.common.models.enums import Segment
from cdmas.simulator.topology import NetworkTopology


def test_all_four_segments_present():
    t = NetworkTopology()
    assert set(t.segments) == set(Segment)


def test_adjacency_is_symmetric():
    t = NetworkTopology()
    for a in t.segments:
        for b in t.neighbors(a):
            assert t.is_adjacent(b, a), f"{a}->{b} not symmetric"


def test_lateral_only_along_edges():
    t = NetworkTopology()
    # internal and public-facing are NOT directly adjacent (must go via server).
    assert not t.is_adjacent(Segment.INTERNAL, Segment.PUBLIC_FACING)
    assert t.is_adjacent(Segment.INTERNAL, Segment.SERVER)


def test_subset_topology_drops_missing_neighbors():
    t = NetworkTopology([Segment.INTERNAL, Segment.SERVER])
    assert t.neighbors(Segment.INTERNAL) == {Segment.SERVER}
    assert Segment.SEC_MON not in t.neighbors(Segment.INTERNAL)
