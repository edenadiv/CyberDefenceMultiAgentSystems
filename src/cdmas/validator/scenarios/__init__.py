"""The six SRS validation scenarios (SRS §8, SDD §7.4).

Each module exposes ``run()`` (-> ScenarioResult) and ``criteria(result)`` (the
scenario-specific success conditions). ``SCENARIOS`` is the ordered registry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from cdmas.validator.harness import ScenarioResult
from cdmas.validator.scenarios import (
    scenario_1_ddos,
    scenario_2_multi,
    scenario_3_contention,
    scenario_4_zeroday,
    scenario_5_failure,
    scenario_6_voting,
)

Scenario = tuple[
    str, Callable[[], Awaitable[ScenarioResult]], Callable[[ScenarioResult], dict[str, bool]]
]

SCENARIOS: list[Scenario] = [
    ("Scenario 1 - Single DDoS", scenario_1_ddos.run, scenario_1_ddos.criteria),
    ("Scenario 2 - Multi-Segment", scenario_2_multi.run, scenario_2_multi.criteria),
    ("Scenario 3 - Resource Contention", scenario_3_contention.run, scenario_3_contention.criteria),
    ("Scenario 4 - Zero-Day", scenario_4_zeroday.run, scenario_4_zeroday.criteria),
    ("Scenario 5 - Agent Failure", scenario_5_failure.run, scenario_5_failure.criteria),
    ("Scenario 6 - Voting Protocol", scenario_6_voting.run, scenario_6_voting.criteria),
]
