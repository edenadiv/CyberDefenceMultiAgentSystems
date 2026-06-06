from cdmas.agents.rca.policy import proportionality_score, select_proportional_action
from cdmas.common.models.enums import AttackType, ResponseType


def test_low_severity_returns_monitor():
    assert select_proportional_action(0.1, AttackType.DDOS).type is ResponseType.MONITOR


def test_volumetric_attacks_throttle_to_preserve_availability():
    # A DDoS is throttled, not quarantined (quarantine would cause an outage).
    assert select_proportional_action(0.9, AttackType.DDOS).type is ResponseType.THROTTLE
    assert select_proportional_action(0.97, AttackType.DDOS).type is ResponseType.BLOCK


def test_host_compromise_escalates_to_quarantine():
    assert select_proportional_action(0.95, AttackType.LATERAL).type is ResponseType.QUARANTINE
    assert select_proportional_action(0.7, AttackType.LATERAL).type is ResponseType.REDEPLOY
    assert select_proportional_action(0.4, AttackType.LATERAL).type is ResponseType.BLOCK


def test_proportionality_always_above_threshold():
    for atk in (AttackType.DDOS, AttackType.LATERAL, AttackType.PORT_SCAN):
        for sev in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0):
            assert proportionality_score(select_proportional_action(sev, atk)) >= 0.7
