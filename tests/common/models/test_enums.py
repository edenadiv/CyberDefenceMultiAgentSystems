from cdmas.common.models.enums import (
    AttackType,
    Classification,
    ResourceType,
    ResponseType,
    Segment,
    VoteDecision,
)


def test_segment_values():
    assert Segment.PUBLIC_FACING == "public-facing"
    assert {s.value for s in Segment} == {"internal", "server", "public-facing", "sec-mon"}


def test_classification_and_response():
    assert Classification.CONFIRMED_THREAT == "CONFIRMED_THREAT"
    assert ResponseType.QUARANTINE == "QUARANTINE"
    assert ResourceType.QUARANTINE_SLOT == "QUARANTINE_SLOT"
    assert VoteDecision.ACCEPT == "ACCEPT"
    assert AttackType.ZERO_DAY == "ZERO_DAY"
