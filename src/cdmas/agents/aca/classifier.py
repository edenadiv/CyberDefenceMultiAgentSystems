"""Hybrid threat classifier: RandomForest (signatures) + IsolationForest (novelty).

Known attack types are learned by a RandomForest; zero-day / novel traffic that matches no
signature is caught by an IsolationForest trained on NORMAL traffic only (SDD §2.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from cdmas.agents._common.features import attack_type_for_label
from cdmas.common.models.enums import AttackType, Classification

_CONFIRM_CONFIDENCE = 0.6
_NOVELTY_FACTOR = 4.0  # multiple of the 99th-pct training NN distance that counts as novel


@dataclass
class Verdict:
    classification: Classification
    attack_type: AttackType
    severity: float
    confidence: float
    novelty: float


class HybridClassifier:
    def __init__(self, *, confirm_confidence: float = _CONFIRM_CONFIDENCE) -> None:
        self.rf = RandomForestClassifier(n_estimators=60, random_state=0)
        # Distance-based novelty over ALL known traffic: a point far from every known
        # sample is a zero-day. (Distance reacts to features that were constant in
        # training, which tree-based detectors cannot isolate on.)
        self.nn = NearestNeighbors(n_neighbors=1)
        self.scaler = StandardScaler()
        self.confirm_confidence = confirm_confidence
        self._novelty_threshold = float("inf")
        self._x: list[list[float]] = []
        self._y: list[str] = []
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def fit(self, x: list[list[float]], y: list[str]) -> None:
        self._x = list(x)
        self._y = list(y)
        self._refit()

    def _refit(self) -> None:
        xs = self.scaler.fit_transform(np.array(self._x, dtype=float))
        self.rf.fit(xs, self._y)
        self.nn.fit(xs)
        # Threshold = a multiple of the 99th-pct nearest-neighbour distance within training.
        train_nn = self.nn.kneighbors(xs, n_neighbors=2)[0][:, 1]
        self._novelty_threshold = float(np.percentile(train_nn, 99)) * _NOVELTY_FACTOR + 1e-9
        self._fitted = True

    def _train_accuracy(self) -> float:
        xs = self.scaler.transform(np.array(self._x, dtype=float))
        return float(self.rf.score(xs, self._y))

    def predict(self, features: list[float]) -> Verdict:
        if not self._fitted:
            raise RuntimeError("classifier not fitted")
        xs = self.scaler.transform(np.array([features], dtype=float))
        proba = self.rf.predict_proba(xs)[0]
        classes = list(self.rf.classes_)
        best = int(np.argmax(proba))
        label = str(classes[best])
        confidence = float(proba[best])
        nn_dist = float(self.nn.kneighbors(xs, n_neighbors=1)[0][0, 0])
        novelty = nn_dist
        is_outlier = nn_dist > self._novelty_threshold
        # An *extreme* outlier (far beyond any known traffic) is a zero-day regardless of
        # the RF guess; a merely strong known attack is not.
        is_extreme = nn_dist > self._novelty_threshold * 5.0

        if is_extreme:
            return Verdict(
                Classification.SUSPICIOUS,
                AttackType.NOVEL,
                severity=0.55,
                confidence=confidence,
                novelty=novelty,
            )
        if label != "NORMAL" and confidence >= self.confirm_confidence:
            return Verdict(
                Classification.CONFIRMED_THREAT,
                attack_type_for_label(label),
                severity=min(0.99, 0.6 + 0.39 * confidence),
                confidence=confidence,
                novelty=novelty,
            )
        if label != "NORMAL":
            return Verdict(
                Classification.SUSPICIOUS,
                attack_type_for_label(label),
                severity=0.4 + 0.3 * confidence,
                confidence=confidence,
                novelty=novelty,
            )
        if is_outlier:
            # Predicted normal but anomalous -> treat as a novel suspicious pattern.
            return Verdict(
                Classification.SUSPICIOUS,
                AttackType.NOVEL,
                severity=0.5,
                confidence=confidence,
                novelty=novelty,
            )
        return Verdict(Classification.NORMAL, AttackType.NOVEL, 0.0, confidence, novelty)

    def partial_update(self, features: list[float], label: str) -> float:
        """Incrementally learn a labeled example; return train-accuracy delta (FR-08)."""
        before = self._train_accuracy()
        self._x.append(list(features))
        self._y.append(label)
        self._refit()
        return self._train_accuracy() - before
