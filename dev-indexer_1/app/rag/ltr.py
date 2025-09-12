from __future__ import annotations

from typing import Iterable, List


class _LinearLTR:
	def __init__(self, weights: List[float] | None = None) -> None:
		# Match feature count from feature_assembler (similarity_primary, log_length, bias)
		self.weights = weights or [0.7, 0.2, 0.1]

	def score(self, features: List[float]) -> float:
		w = self.weights
		n = min(len(w), len(features))
		s = sum(w[i] * float(features[i]) for i in range(n))
		return float(s)

	def score_matrix(self, X: Iterable[Iterable[float]]) -> List[float]:
		return [self.score(list(row)) for row in X]


# Global instance used by router and tests
GLOBAL_LTR_MODEL = _LinearLTR()

