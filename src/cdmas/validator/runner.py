"""Run all six scenarios, aggregate verdicts, and build an FR coverage matrix."""

from __future__ import annotations

from dataclasses import dataclass, field

from cdmas.validator.constraints import ConstraintResult


@dataclass
class ScenarioOutcome:
    name: str
    criteria: dict[str, bool]
    constraints: list[ConstraintResult]
    social_welfare: float

    @property
    def passed(self) -> bool:
        no_fail = all(c.status != "FAIL" for c in self.constraints)
        return all(self.criteria.values()) and no_fail


@dataclass
class ValidationReport:
    outcomes: list[ScenarioOutcome] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.outcomes) and all(o.passed for o in self.outcomes)

    @property
    def fr_pass(self) -> set[str]:
        return {c.fr_id for o in self.outcomes for c in o.constraints if c.status == "PASS"}

    @property
    def fr_fail(self) -> set[str]:
        return {c.fr_id for o in self.outcomes for c in o.constraints if c.status == "FAIL"}


async def run_all() -> ValidationReport:
    from cdmas.validator.scenarios import SCENARIOS

    report = ValidationReport()
    for name, run_fn, criteria_fn in SCENARIOS:
        result = await run_fn()
        report.outcomes.append(
            ScenarioOutcome(
                name=name,
                criteria=criteria_fn(result),
                constraints=result.constraints,
                social_welfare=result.metrics.social_welfare,
            )
        )
    return report
