import pytest

from cdmas.common.messaging.acl import ACLMessage, SchemaViolation, parse_message
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


def test_build_and_serialize():
    m = ACLMessage(
        performative=Performative.INFORM,
        sender="TMA:seg1",
        receiver="BROADCAST",
        topic=Topic.ALERTS,
        content={"alert_id": "a1"},
    )
    assert m.msg_id
    assert m.lamport_ts == 0  # stamped by the bus on publish
    raw = m.model_dump_json()
    again = ACLMessage.model_validate_json(raw)
    assert again.sender == "TMA:seg1"
    assert again.topic is Topic.ALERTS


def test_parse_rejects_malformed():
    with pytest.raises(SchemaViolation):
        parse_message('{"performative": "INFORM"}')  # missing required fields


def test_parse_rejects_unknown_performative():
    bad = '{"performative":"FROBNICATE","sender":"a","receiver":"b","topic":"alerts","content":{}}'
    with pytest.raises(SchemaViolation):
        parse_message(bad)
