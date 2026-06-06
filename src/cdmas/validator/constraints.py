"""Constraint checkers asserting SRS functional requirements over an event log.

Each checker returns PASS, FAIL, or NA (not applicable — the requirement wasn't exercised
in this scenario). A scenario passes if it has no FAILs; FR coverage across the whole suite
is the set of FRs that PASS in at least one scenario.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal, Protocol

from cdmas.common.logging.event_log import EventLog, EventType

Status = Literal["PASS", "FAIL", "NA"]


class Metrics(Protocol):
    dr: float
    fpr: float
    mttr_alert_ms: float
    mttr_response_ms: float
    availability: float
    resource_overhead: float
    social_welfare: float
    attacker_utility: float
    concurrent_incidents: int


@dataclass(frozen=True)
class ConstraintResult:
    fr_id: str
    description: str
    status: Status
    observed: str
    expected: str

    @property
    def passed(self) -> bool:
        return self.status != "FAIL"


@dataclass
class CheckContext:
    events: list[EventLog]
    metrics: Metrics | None


Constraint = Callable[[CheckContext], ConstraintResult]
Where = Callable[[EventLog], bool]


def select(
    events: list[EventLog],
    *,
    event_type: EventType | None = None,
    signal: str | None = None,
    where: Where | None = None,
) -> list[EventLog]:
    out: list[EventLog] = []
    for e in events:
        if event_type is not None and e.event_type is not event_type:
            continue
        if signal is not None and e.payload.get("signal") != signal:
            continue
        if where is not None and not where(e):
            continue
        out.append(e)
    return out


def _res(fr: str, desc: str, status: Status, observed: str, expected: str) -> ConstraintResult:
    return ConstraintResult(fr, desc, status, observed, expected)


# --- factories --------------------------------------------------------------
def latency_lt(
    fr: str,
    desc: str,
    *,
    event_type: EventType,
    bound: int,
    signal: str | None = None,
    where: Where | None = None,
) -> Constraint:
    def check(ctx: CheckContext) -> ConstraintResult:
        evs = select(ctx.events, event_type=event_type, signal=signal, where=where)
        lats = [e.latency_ms for e in evs if e.latency_ms is not None]
        if not lats:
            return _res(fr, desc, "NA", "no events", f"<{bound}ms")
        m = max(lats)
        return _res(fr, desc, "PASS" if m < bound else "FAIL", f"max={m}ms", f"<{bound}ms")

    return check


def metric_cmp(
    fr: str, desc: str, *, attr: str, op: Callable[[float, float], bool], bound: float
) -> Constraint:
    def check(ctx: CheckContext) -> ConstraintResult:
        if ctx.metrics is None:
            return _res(fr, desc, "NA", "no metrics", desc)
        v = float(getattr(ctx.metrics, attr))
        return _res(
            fr,
            desc,
            "PASS" if op(v, bound) else "FAIL",
            f"{attr}={v:.4f}",
            f"{op.__name__} {bound}",
        )

    return check


def all_match(
    fr: str,
    desc: str,
    *,
    event_type: EventType,
    predicate: Where,
    signal: str | None = None,
    where: Where | None = None,
) -> Constraint:
    def check(ctx: CheckContext) -> ConstraintResult:
        evs = select(ctx.events, event_type=event_type, signal=signal, where=where)
        if not evs:
            return _res(fr, desc, "NA", "no events", "all satisfy")
        bad = [e for e in evs if not predicate(e)]
        return _res(
            fr, desc, "PASS" if not bad else "FAIL", f"{len(bad)}/{len(evs)} violate", "all satisfy"
        )

    return check


def max_interval_lte(
    fr: str, desc: str, *, signal: str, bound: float, per_agent: bool = True
) -> Constraint:
    def check(ctx: CheckContext) -> ConstraintResult:
        evs = sorted(select(ctx.events, signal=signal), key=lambda e: e.wall_ms)
        if len(evs) < 2:
            return _res(fr, desc, "NA", f"{len(evs)} events", f"gaps <= {bound}ms")
        groups: dict[str, list[float]] = {}
        for e in evs:
            groups.setdefault(e.agent_id if per_agent else "*", []).append(e.wall_ms)
        worst = 0.0
        for ts in groups.values():
            worst = max([worst, *[b - a for a, b in pairwise(ts)]])
        return _res(
            fr, desc, "PASS" if worst <= bound else "FAIL", f"max gap={worst}ms", f"<={bound}ms"
        )

    return check


# --- latency / interval / metric FRs ---------------------------------------
FR03 = latency_lt("FR-03", "TMA alert <100ms", event_type=EventType.ALERT_PUBLISHED, bound=100)
FR05 = latency_lt("FR-05", "ACA classify <200ms", event_type=EventType.THREAT_CLASSIFIED, bound=200)
FR10 = latency_lt(
    "FR-10",
    "RCA respond <500ms",
    event_type=EventType.ACTION_EXECUTED,
    bound=500,
    signal="response",
    where=lambda e: e.payload.get("severity", 0) >= 0.7,
)
FR15 = latency_lt(
    "FR-15",
    "TIA model update <500ms",
    event_type=EventType.ACTION_EXECUTED,
    bound=500,
    signal="threat_model_update",
)
FR16 = latency_lt(
    "FR-16",
    "correlation <1000ms",
    event_type=EventType.ACTION_EXECUTED,
    bound=1000,
    signal="correlation",
)
FR19 = latency_lt("FR-19", "auction <300ms", event_type=EventType.AUCTION_COMPLETED, bound=300)
FR22 = latency_lt(
    "FR-22", "reclaim <500ms", event_type=EventType.RESOURCE_ALLOCATED, bound=500, signal="reclaim"
)

FR04 = max_interval_lte("FR-04", "baseline update <=60s", signal="baseline_update", bound=60_000)
FR18 = max_interval_lte(
    "FR-18", "priority list <=1s", signal="priority_list", bound=1_000, per_agent=False
)

FR09 = metric_cmp("FR-09", "FPR <10%", attr="fpr", op=operator.lt, bound=0.10)
FR23 = metric_cmp("FR-23", "overhead <40%", attr="resource_overhead", op=operator.lt, bound=0.40)
FR29 = metric_cmp("FR-29", "DR >=90%", attr="dr", op=operator.ge, bound=0.90)
FR30 = metric_cmp(
    "FR-30", "MTTR_response <1000ms", attr="mttr_response_ms", op=operator.lt, bound=1000
)
FR31 = metric_cmp("FR-31", "availability >99%", attr="availability", op=operator.gt, bound=0.99)

# --- predicate FRs ----------------------------------------------------------
FR02 = all_match(
    "FR-02",
    "alerts only on >2 sigma",
    event_type=EventType.ALERT_PUBLISHED,
    predicate=lambda e: e.payload.get("deviation_score", 0) >= 2.0,
)
FR06 = all_match(
    "FR-06",
    "confirmed severity in [0,1]",
    event_type=EventType.THREAT_CLASSIFIED,
    predicate=lambda e: 0.0 <= e.payload.get("severity", -1) <= 1.0,
    where=lambda e: e.payload.get("classification") == "CONFIRMED_THREAT",
)
FR07 = all_match(
    "FR-07",
    "confirmed/suspicious reported",
    event_type=EventType.THREAT_CLASSIFIED,
    predicate=lambda e: e.payload.get("reported") is True,
    where=lambda e: e.payload.get("classification") in {"CONFIRMED_THREAT", "SUSPICIOUS"},
)
FR12 = all_match(
    "FR-12",
    "responses have decision trace",
    event_type=EventType.ACTION_EXECUTED,
    signal="response",
    predicate=lambda e: e.decision_trace is not None,
)
FR13 = all_match(
    "FR-13",
    "proportionality >=0.7",
    event_type=EventType.ACTION_EXECUTED,
    signal="response",
    predicate=lambda e: e.payload.get("proportionality_score", 0) >= 0.7,
)
FR14 = all_match(
    "FR-14",
    "resolution notice present",
    event_type=EventType.INCIDENT_RESOLVED,
    predicate=lambda e: bool(e.payload.get("resolution_id")),
)
FR21 = all_match(
    "FR-21",
    "auction notify <100ms",
    event_type=EventType.AUCTION_COMPLETED,
    predicate=lambda e: e.payload.get("notify_latency_ms", 1e9) < 100,
)
FR32 = all_match(
    "FR-32",
    "rejections carry a reason",
    event_type=EventType.ACTION_EXECUTED,
    signal="rejection",
    predicate=lambda e: bool(e.payload.get("reason")),
)


# --- bespoke FRs ------------------------------------------------------------
def _fr01(ctx: CheckContext) -> ConstraintResult:
    evs = select(ctx.events, signal="sampling")
    rates = [e.payload.get("sample_rate_hz", 0) for e in evs]
    if not rates:
        return _res("FR-01", "TMA samples >=10/s", "NA", "no telemetry", ">=10")
    return _res(
        "FR-01",
        "TMA samples >=10/s",
        "PASS" if min(rates) >= 10 else "FAIL",
        f"min={min(rates)}",
        ">=10",
    )


def _fr08(ctx: CheckContext) -> ConstraintResult:
    if not select(ctx.events, event_type=EventType.INCIDENT_RESOLVED):
        return _res(
            "FR-08", "online learning after resolution", "NA", "no resolutions", ">=1 update"
        )
    updates = select(ctx.events, signal="online_update")
    return _res(
        "FR-08",
        "online learning after resolution",
        "PASS" if updates else "FAIL",
        f"{len(updates)} updates",
        ">=1",
    )


def _fr11(ctx: CheckContext) -> ConstraintResult:
    quarantines = select(
        ctx.events,
        event_type=EventType.ACTION_EXECUTED,
        where=lambda e: e.payload.get("action") == "QUARANTINE",
    )
    if not quarantines:
        return _res(
            "FR-11", "no quarantine without majority", "NA", "no quarantines", "majority-approved"
        )
    majority = {
        e.payload["vote_id"]
        for e in select(ctx.events, event_type=EventType.VOTE_CAST)
        if e.payload.get("accept_count", 0) > e.payload.get("member_count", 0) / 2
    }
    bad = [e for e in quarantines if e.payload.get("vote_id") not in majority]
    return _res(
        "FR-11",
        "no quarantine without majority",
        "PASS" if not bad else "FAIL",
        f"{len(bad)} unauthorized",
        "all approved",
    )


def _fr17(ctx: CheckContext) -> ConstraintResult:
    correlated = select(
        ctx.events, signal="correlation", where=lambda e: len(e.payload.get("segments", [])) >= 2
    )
    if not correlated:
        return _res(
            "FR-17", "multi-segment -> coalition", "NA", "no correlation", "coalition formed"
        )
    coalitions = select(ctx.events, event_type=EventType.COALITION_FORMED)
    return _res(
        "FR-17",
        "multi-segment -> coalition",
        "PASS" if coalitions else "FAIL",
        f"{len(coalitions)} coalitions",
        ">=1",
    )


def _fr20(ctx: CheckContext) -> ConstraintResult:
    auctions = select(ctx.events, event_type=EventType.AUCTION_COMPLETED)
    if not auctions:
        return _res("FR-20", "auction grants top severity", "NA", "no auctions", "winners=top-k")
    bad = 0
    for e in auctions:
        bids: dict[str, float] = e.payload.get("bids", {})
        slots: int = e.payload.get("slots", 0)
        expected = {k for k, _ in sorted(bids.items(), key=lambda kv: kv[1], reverse=True)[:slots]}
        if set(e.payload.get("granted", [])) != expected:
            bad += 1
    return _res(
        "FR-20",
        "auction grants top severity",
        "PASS" if bad == 0 else "FAIL",
        f"{bad} mis-allocated",
        "winners=top-k",
    )


def _attack_actions(ctx: CheckContext, attack_type: str) -> list[EventLog]:
    return select(
        ctx.events,
        signal="attack_action",
        where=lambda e: e.payload.get("attack_type") == attack_type,
    )


def _fr24(ctx: CheckContext) -> ConstraintResult:
    ddos = _attack_actions(ctx, "DDOS")
    if not ddos:
        return _res("FR-24", "DDoS randomized IPs", "NA", "no DDoS", ">=N unique IPs")
    bad = [
        e
        for e in ddos
        if len(set(e.payload.get("src_ips", []))) < e.payload.get("min_unique_ips", 20)
    ]
    return _res(
        "FR-24",
        "DDoS randomized IPs",
        "PASS" if not bad else "FAIL",
        f"{len(bad)} under-diverse",
        ">=N unique",
    )


def _fr25(ctx: CheckContext) -> ConstraintResult:
    scans = _attack_actions(ctx, "PORT_SCAN")
    if not scans:
        return _res("FR-25", "scan pseudo-random order", "NA", "no scans", "non-monotonic")
    bad = [e for e in scans if e.payload.get("ports", []) == sorted(e.payload.get("ports", []))]
    return _res(
        "FR-25",
        "scan pseudo-random order",
        "PASS" if not bad else "FAIL",
        f"{len(bad)} sorted",
        "varied",
    )


def _fr26(ctx: CheckContext) -> ConstraintResult:
    if not _attack_actions(ctx, "ZERO_DAY"):
        return _res("FR-26", "zero-day detected as novel", "NA", "no zero-day", "novel detection")
    novel = select(
        ctx.events,
        event_type=EventType.THREAT_CLASSIFIED,
        where=lambda e: e.payload.get("attack_type") in {"NOVEL", "ZERO_DAY"},
    )
    return _res(
        "FR-26",
        "zero-day detected as novel",
        "PASS" if novel else "FAIL",
        f"{len(novel)} novel",
        ">=1",
    )


def _fr27(ctx: CheckContext) -> ConstraintResult:
    actions = select(ctx.events, signal="attack_action")
    if not actions:
        return _res("FR-27", "attackers log actions", "NA", "no attackers", ">=1 logged")
    return _res("FR-27", "attackers log actions", "PASS", f"{len(actions)} logged", ">=1")


def _fr28(ctx: CheckContext) -> ConstraintResult:
    actions = select(ctx.events, signal="attack_action")
    if not actions:
        return _res("FR-28", "attacker (in)dependence", "NA", "no attackers", "matches mode")
    coordinated = [e for e in actions if e.payload.get("mode") == "coordinated"]
    if coordinated:
        ts = sorted(e.wall_ms for e in coordinated)
        synced = (max(ts) - min(ts)) < 50
        return _res(
            "FR-28",
            "attacker (in)dependence",
            "PASS" if synced else "FAIL",
            f"spread={max(ts) - min(ts)}ms",
            "synced",
        )
    return _res("FR-28", "attacker (in)dependence", "PASS", "independent", "unsynced")


def _fr33(ctx: CheckContext) -> ConstraintResult:
    if ctx.metrics is None:
        return _res("FR-33", ">=5 concurrent incidents", "NA", "no metrics", ">=5")
    n = ctx.metrics.concurrent_incidents
    if n < 5:
        return _res("FR-33", ">=5 concurrent incidents", "NA", f"{n} incidents", ">=5")
    return _res("FR-33", ">=5 concurrent incidents", "PASS", f"{n} handled", ">=5")


def _fr34(ctx: CheckContext) -> ConstraintResult:
    failures = select(ctx.events, event_type=EventType.AGENT_FAILED)
    if not failures:
        return _res("FR-34", "coverage reassigned <2s", "NA", "no failures", "<2000ms")
    reassigns = select(ctx.events, signal="coverage_reassigned")
    bad = 0
    for f in failures:
        nxt = [
            r
            for r in reassigns
            if r.payload.get("segment") == f.payload.get("segment") and r.wall_ms >= f.wall_ms
        ]
        if not nxt or (min(r.wall_ms for r in nxt) - f.wall_ms) > 2000:
            bad += 1
    return _res(
        "FR-34",
        "coverage reassigned <2s",
        "PASS" if bad == 0 else "FAIL",
        f"{bad} slow/missing",
        "<2000ms",
    )


FR01, FR08, FR11, FR17, FR20 = _fr01, _fr08, _fr11, _fr17, _fr20
FR24, FR25, FR26, FR27, FR28, FR33, FR34 = _fr24, _fr25, _fr26, _fr27, _fr28, _fr33, _fr34


ALL_CONSTRAINTS: list[Constraint] = [
    FR01,
    FR02,
    FR03,
    FR04,
    FR05,
    FR06,
    FR07,
    FR08,
    FR09,
    FR10,
    FR11,
    FR12,
    FR13,
    FR14,
    FR15,
    FR16,
    FR17,
    FR18,
    FR19,
    FR20,
    FR21,
    FR22,
    FR23,
    FR24,
    FR25,
    FR26,
    FR27,
    FR28,
    FR29,
    FR30,
    FR31,
    FR32,
    FR33,
    FR34,
]


def check_all(ctx: CheckContext) -> list[ConstraintResult]:
    return [c(ctx) for c in ALL_CONSTRAINTS]


def covered_frs() -> set[str]:
    return {c(CheckContext(events=[], metrics=None)).fr_id for c in ALL_CONSTRAINTS}
