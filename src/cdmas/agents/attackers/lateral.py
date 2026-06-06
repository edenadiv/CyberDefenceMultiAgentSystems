"""Lateral movement attacker — quiet host-to-host movement after a breach."""

from __future__ import annotations

from typing import Any

from cdmas.agents.attackers.base_attacker import AttackerAgent
from cdmas.common.models.enums import AttackType


class LateralMovementAgent(AttackerAgent):
    attack_type = AttackType.LATERAL

    def _action_payload(self) -> dict[str, Any]:
        return {"technique": "smb-enumeration", "persistence": True}
