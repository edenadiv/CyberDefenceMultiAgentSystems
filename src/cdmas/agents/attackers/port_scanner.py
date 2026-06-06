"""Port scanner — probes ports in pseudo-random order, varying per run (FR-25)."""

from __future__ import annotations

from typing import Any

import numpy as np

from cdmas.agents.attackers.base_attacker import AttackerAgent
from cdmas.common.models.enums import AttackType


class PortScanner(AttackerAgent):
    attack_type = AttackType.PORT_SCAN

    def _action_payload(self) -> dict[str, Any]:
        rng = np.random.default_rng(self.seed)
        ports = [int(p) for p in rng.permutation(np.arange(1, 1025))[:50]]
        return {"ports": ports}
