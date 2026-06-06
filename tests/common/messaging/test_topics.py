from cdmas.common.messaging.topics import TOPIC_REGISTRY, Topic, can_publish, can_subscribe


def test_topic_values():
    assert Topic.ALERTS == "alerts"
    assert Topic.THREAT_REPORTS == "threat-reports"


def test_registry_matches_sdd_table_2():
    # TMA publishes alerts; ACA subscribes.
    assert can_publish("TMA", Topic.ALERTS)
    assert can_subscribe("ACA", Topic.ALERTS)
    assert not can_publish("ACA", Topic.ALERTS)
    # RAA is the only subscriber of resource-bids.
    assert can_subscribe("RAA", Topic.RESOURCE_BIDS)
    assert can_publish("RCA", Topic.RESOURCE_BIDS)


def test_every_topic_registered():
    assert set(TOPIC_REGISTRY) == set(Topic)
