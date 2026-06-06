"""Acceptance gate: all six SRS validation scenarios must pass (SRS §8)."""

import pytest

from cdmas.validator.runner import run_all


@pytest.mark.acceptance
async def test_all_six_scenarios_pass():
    report = await run_all()
    failed = [o.name for o in report.outcomes if not o.passed]
    assert not failed, f"failed scenarios: {failed}"
    assert len(report.outcomes) == 6
    assert not report.fr_fail, f"failing FRs: {sorted(report.fr_fail)}"
    # Every scenario must clear the Social Welfare threshold.
    assert all(o.social_welfare >= 0.80 for o in report.outcomes)
    assert report.passed
