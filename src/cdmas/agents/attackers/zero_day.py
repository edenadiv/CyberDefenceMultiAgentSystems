"""Zero-day emulator — traffic matching no known signature (FR-26)."""

from __future__ import annotations

from typing import Any

from cdmas.agents.attackers.base_attacker import AttackerAgent
from cdmas.common.models.enums import AttackType


class ZeroDayEmulator(AttackerAgent):
    attack_type = AttackType.ZERO_DAY

    def _action_payload(self) -> dict[str, Any]:
        return {"signature": "none", "novel": True}
