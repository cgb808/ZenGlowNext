from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ACOPath:
    factors: List[str]
    score: float
    provenance: Dict[str, Any]

class ACOExplorer:
    """Stub ACO explorer producing diverse factor paths.

    Future: Use pheromone matrix + heuristic visibility; apply diversity penalty.
    """
    def __init__(self, max_paths: int = 5, random_seed: int | None = None):
        self.max_paths = max_paths
        if random_seed is not None:
            random.seed(random_seed)

    _FACTOR_POOL = [
        "vitamin_d", "morning_sunlight", "low_sugar_diet",
        "sleep_consistency", "hydration", "resistance_training",
        "mindfulness", "cold_exposure", "probiotic_foods", "blue_light_block"
    ]

    def find_paths(self, query: str) -> List[ACOPath]:
        k = min(self.max_paths, 5)
        paths: List[ACOPath] = []
        pool = self._FACTOR_POOL.copy()
        random.shuffle(pool)
        for i in range(k):
            # Variable length 2-4 factors
            length = random.randint(2,4)
            factors = random.sample(pool, length)
            # Synthetic relevance score influenced lightly by query length
            base = random.random()*0.4 + 0.6  # 0.6 - 1.0
            modifier = min(0.2, len(query)/400.0)
            score = base + modifier
            paths.append(ACOPath(factors=factors, score=round(score,4), provenance={
                "diversity_rank": i+1,
                "seed": random.randint(0, 999999),
            }))
        return paths
