"""Export all six recorded scenario runs + validation summary as JSON for the dashboard.

Produces a self-contained file the React frontend loads (so the dashboard works offline,
and can still connect to a live simulator WebSocket when one is available). Each scenario
carries its own recording and topology (scenarios activate different segment sets).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cdmas.simulator.topology import NetworkTopology
from cdmas.validator.scenarios import SCENARIOS


async def build_export() -> dict[str, Any]:
    replays: list[dict[str, Any]] = []
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
        topology = NetworkTopology(result.segments)
        replays.append(
            {
                "scenario": name,
                "duration_ms": max((e.wall_ms for e in result.events), default=0.0),
                "topology": {
                    "segments": [s.value for s in topology.segments],
                    "adjacency": topology.adjacency_view(),
                },
                "events": [e.model_dump(mode="json") for e in result.events],
                "metrics": result.metrics.model_dump(mode="json"),
                "packets": result.packets,
                "messages": result.messages,
            }
        )

    return {"replays": replays, "validation": validation}


def write_export(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def main() -> None:
    import asyncio
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("frontend/src/data/replay.json")
    data = asyncio.run(build_export())
    write_export(target, data)
    events = sum(len(r["events"]) for r in data["replays"])
    packets = sum(len(r["packets"]) for r in data["replays"])
    size_kb = target.stat().st_size / 1024
    print(
        f"Wrote {target} ({len(data['replays'])} replays, {events} events, "
        f"{packets} packets, {len(data['validation'])} scenarios, {size_kb:.0f} KB)"
    )


if __name__ == "__main__":
    main()
