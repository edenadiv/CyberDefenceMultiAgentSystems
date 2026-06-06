"""Export a recorded scenario run + validation summary as JSON for the dashboard.

Produces a self-contained file the React frontend loads (so the dashboard works offline,
and can still connect to a live simulator WebSocket when one is available).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cdmas.common.models.enums import Segment
from cdmas.simulator.topology import NetworkTopology
from cdmas.validator.scenarios import SCENARIOS


async def build_export() -> dict[str, Any]:
    topology = NetworkTopology(list(Segment))
    replay: dict[str, Any] | None = None
    validation: list[dict[str, Any]] = []

    for name, run_fn, criteria_fn in SCENARIOS:
        result = await run_fn()
        criteria = criteria_fn(result)
        validation.append(
            {
                "name": name,
                "passed": all(criteria.values()) and not result.failed,
                "social_welfare": result.metrics.social_welfare,
                "criteria": criteria,
                "constraints": [
                    {
                        "fr_id": c.fr_id,
                        "status": c.status,
                        "description": c.description,
                        "observed": c.observed,
                    }
                    for c in result.constraints
                ],
            }
        )
        # Use the richest run (multi-segment) for the animated dashboard replay.
        if replay is None and "Multi-Segment" in name:
            replay = {
                "scenario": name,
                "duration_ms": max((e.wall_ms for e in result.events), default=0.0),
                "events": [e.model_dump(mode="json") for e in result.events],
                "metrics": result.metrics.model_dump(mode="json"),
            }

    if replay is None:  # fallback to the first scenario
        first = await SCENARIOS[0][1]()
        replay = {
            "scenario": SCENARIOS[0][0],
            "duration_ms": max((e.wall_ms for e in first.events), default=0.0),
            "events": [e.model_dump(mode="json") for e in first.events],
            "metrics": first.metrics.model_dump(mode="json"),
        }

    return {
        "topology": {
            "segments": [s.value for s in topology.segments],
            "adjacency": topology.adjacency_view(),
        },
        "replay": replay,
        "validation": validation,
    }


def write_export(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def main() -> None:
    import asyncio
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("frontend/src/data/replay.json")
    data = asyncio.run(build_export())
    write_export(target, data)
    events = len(data["replay"]["events"])
    print(f"Wrote {target} ({events} events, {len(data['validation'])} scenarios)")


if __name__ == "__main__":
    main()
