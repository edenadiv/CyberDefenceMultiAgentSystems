"""`cdmas-validator` CLI: run the six scenarios and print the report."""

from __future__ import annotations

import asyncio

from cdmas.validator.runner import run_all


def main() -> int:
    report = asyncio.run(run_all())
    for o in report.outcomes:
        flag = "PASS" if o.passed else "FAIL"
        print(f"[{flag}] {o.name}  (SW={o.social_welfare:.3f})")
        for k, v in o.criteria.items():
            print(f"    {'PASS' if v else 'FAIL'}  {k}")
    na = {f"FR-{n:02d}" for n in range(1, 35)} - report.fr_pass - report.fr_fail
    print(
        f"\nFR coverage: {len(report.fr_pass)} passed, {len(report.fr_fail)} failed, "
        f"{len(na)} not exercised"
    )
    if report.fr_fail:
        print(f"  failing FRs: {sorted(report.fr_fail)}")
    print(f"\nOVERALL: {'PASS' if report.passed else 'FAIL'}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
