"""Online learning wrapper for the ACA classifier (FR-08, SDD §2.3)."""

from __future__ import annotations

from cdmas.agents.aca.classifier import HybridClassifier


class OnlineLearner:
    def __init__(self, classifier: HybridClassifier) -> None:
        self.clf = classifier
        self.improvement_rate = 0.0

    def update(self, features: list[float], label: str) -> float:
        delta = self.clf.partial_update(features, label)
        self.improvement_rate = delta
        return delta
