import logging
from typing import List, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

class RankingPipeline:
	def __init__(self, model, feature_assembler):
		self.model = model
		self.feature_assembler = feature_assembler

	def rank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
		"""
		Ranks the provided documents for the given query.
		"""
		logger.info(f"Ranking {len(docs)} docs for query: {query}")
		features = self.feature_assembler.assemble(query, docs)
		logger.debug(f"Assembled features: {features}")
		scores = self.model.predict(features)
		logger.debug(f"LTR scores: {scores}")
		for doc, score in zip(docs, scores):
			doc['score'] = float(score)
		ranked = sorted(docs, key=lambda d: d['score'], reverse=True)
		logger.info(f"Top doc after ranking: {ranked[0] if ranked else None}")
		return ranked
