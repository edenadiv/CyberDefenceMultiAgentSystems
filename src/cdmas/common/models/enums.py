"""Domain enumerations shared across message payloads (SRS §2, §3; SDD §3.2)."""

from enum import StrEnum


class Segment(StrEnum):
    INTERNAL = "internal"
    SERVER = "server"
    PUBLIC_FACING = "public-facing"
    SEC_MON = "sec-mon"


class Performative(StrEnum):
    INFORM = "INFORM"
    REQUEST = "REQUEST"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CALL_FOR_PROPOSAL = "CALL-FOR-PROPOSAL"
    BID = "BID"
    FAILURE = "FAILURE"
    NOT_UNDERSTOOD = "NOT-UNDERSTOOD"


class AttackType(StrEnum):
    VOLUME_SPIKE = "VOLUME_SPIKE"
    PORT_SCAN = "PORT_SCAN"
    LATERAL = "LATERAL"
    NOVEL = "NOVEL"
    DDOS = "DDOS"
    RANSOMWARE = "RANSOMWARE"
    ZERO_DAY = "ZERO_DAY"


class Classification(StrEnum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    CONFIRMED_THREAT = "CONFIRMED_THREAT"


class ResponseType(StrEnum):
    THROTTLE = "THROTTLE"
    BLOCK = "BLOCK"
    REDEPLOY = "REDEPLOY"
    QUARANTINE = "QUARANTINE"
    MONITOR = "MONITOR"


class ResourceType(StrEnum):
    DPI_SLOT = "DPI_SLOT"
    QUARANTINE_SLOT = "QUARANTINE_SLOT"
    CPU_BUDGET = "CPU_BUDGET"


class VoteDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
