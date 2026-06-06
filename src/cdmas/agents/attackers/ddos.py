"""DDoS attacker — floods a segment with randomized source IPs (FR-24)."""

from __future__ import annotations

from typing import Any

import numpy as np

from cdmas.agents.attackers.base_attacker import AttackerAgent
from cdmas.common.models.enums import AttackType

_MIN_UNIQUE_IPS = 20


class DDoSAttacker(AttackerAgent):
    attack_type = AttackType.DDOS

    def _action_payload(self) -> dict[str, Any]:
        rng = np.random.default_rng(self.seed)
        n = max(_MIN_UNIQUE_IPS, int(self.intensity * 20))
        src_ips = [
            f"203.0.{int(rng.integers(1, 255))}.{int(rng.integers(1, 255))}" for _ in range(n)
        ]
        return {"src_ips": src_ips, "min_unique_ips": _MIN_UNIQUE_IPS}
