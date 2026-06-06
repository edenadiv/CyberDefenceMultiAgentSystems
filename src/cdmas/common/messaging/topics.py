"""Pub/sub topic registry (SDD §3.1.2, Table 2).

Agent *types* (TMA, ACA, RCA, TIA, RAA) are the publish/subscribe principals.
"""

from enum import StrEnum


class Topic(StrEnum):
    ALERTS = "alerts"
    THREAT_REPORTS = "threat-reports"
    THREAT_INTEL = "threat-intel"
    RESOURCE_BIDS = "resource-bids"
    RESOURCE_GRANTS = "resource-grants"
    COALITION = "coalition"
    VOTES = "votes"
    RESOLUTION = "resolution"


# topic -> {"publishers": {...}, "subscribers": {...}}
TOPIC_REGISTRY: dict[Topic, dict[str, set[str]]] = {
    Topic.ALERTS: {"publishers": {"TMA"}, "subscribers": {"ACA"}},
    Topic.THREAT_REPORTS: {"publishers": {"ACA"}, "subscribers": {"RCA", "TIA"}},
    Topic.THREAT_INTEL: {"publishers": {"TIA", "ACA"}, "subscribers": {"ACA", "RCA", "RAA"}},
    Topic.RESOURCE_BIDS: {"publishers": {"TMA", "ACA", "RCA"}, "subscribers": {"RAA"}},
    Topic.RESOURCE_GRANTS: {"publishers": {"RAA"}, "subscribers": {"TMA", "ACA", "RCA", "TIA"}},
    Topic.COALITION: {"publishers": {"TIA"}, "subscribers": {"ACA", "RCA", "RAA"}},
    Topic.VOTES: {"publishers": {"RCA"}, "subscribers": {"ACA", "RCA", "TIA", "RAA"}},
    Topic.RESOLUTION: {"publishers": {"RCA"}, "subscribers": {"ACA", "RCA", "TIA", "RAA"}},
}


def can_publish(agent_type: str, topic: Topic) -> bool:
    return agent_type in TOPIC_REGISTRY[topic]["publishers"]


def can_subscribe(agent_type: str, topic: Topic) -> bool:
    return agent_type in TOPIC_REGISTRY[topic]["subscribers"]
