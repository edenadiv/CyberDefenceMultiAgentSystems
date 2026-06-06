import pytest
from pydantic import ValidationError

from cdmas.common.models.alert import Alert
from cdmas.common.models.enums import AttackType, Classification, Segment
from cdmas.common.models.threat_report import ThreatReport


def test_alert_roundtrip():
    a = Alert(
        segment=Segment.PUBLIC_FACING,
        anomaly_type=AttackType.VOLUME_SPIKE,
        deviation_score=4.2,
        src_ips=["10.0.1.5"],
        dst_port=443,
        traffic_volume=9800,
        baseline_mean=400,
        baseline_std=50,
    )
    assert a.alert_id  # auto uuid
    again = Alert.model_validate_json(a.model_dump_json())
    assert again.deviation_score == 4.2
    assert again.segment is Segment.PUBLIC_FACING


def test_threat_report_severity_bounds():
    with pytest.raises(ValidationError):
        ThreatReport(
            alert_id="x",
            classification=Classification.CONFIRMED_THREAT,
            attack_type=AttackType.DDOS,
            severity=1.5,  # out of [0,1]
            segment=Segment.PUBLIC_FACING,
            confidence=0.9,
        )
