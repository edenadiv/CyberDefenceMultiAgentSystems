"""`cdmas-attacker` entrypoint.

Attack type and target come from the environment (CDMAS_AGENT_ID like "ATK:ddos",
CDMAS_AGENT_SEGMENT). Attackers drive the simulator's /inject-attack endpoint.
"""

from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "cdmas-attacker runs inside the simulator harness or against a live simulator's "
        "/inject-attack endpoint. Use the validator scenarios to drive attackers."
    )


if __name__ == "__main__":
    main()
