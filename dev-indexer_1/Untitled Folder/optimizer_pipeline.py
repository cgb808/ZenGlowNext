from __future__ import annotations
from typing import List, Dict, Any
import asyncio
from .optimizers.aco import ACOExplorer, ACOPath
from .optimizers.pso import PSOOptimizer, PSOResult

class OptimizerPipeline:
    """Coordinates ACO exploration followed by PSO exploitation.

    Current implementation is synchronous & simplistic; future versions may:
      - Parallelize PSO refinement per path.
      - Early terminate on threshold objective.
      - Integrate predictive adjustments.
    """
    def __init__(self, max_paths: int = 5):
        self.aco = ACOExplorer(max_paths=max_paths)
        self.pso = PSOOptimizer()

    async def optimize(self, query: str) -> Dict[str, Any]:
        paths: List[ACOPath] = self.aco.find_paths(query)
        # Run PSO refinements concurrently (refine_path assumed CPU-light or IO-bound stub)
        tasks = [asyncio.to_thread(self.pso.refine_path, path.factors, query) for path in paths]
        results: List[PSOResult] = await asyncio.gather(*tasks) if tasks else []
        refined: List[Dict[str, Any]] = []
        for path, pso_res in zip(paths, results):
            # simple deterministic pseudo-embedding (16D) based on factor & query hashes for now
            import hashlib, math
            base_str = "|".join([query] + pso_res.factors + list(sorted(pso_res.parameters.keys())))
            digest = hashlib.sha256(base_str.encode("utf-8")).digest()
            # take first 16 bytes -> map to floats [0,1)
            emb = [round(b / 255.0, 6) for b in digest[:16]]
            refined.append({
                "factors": pso_res.factors,
                "parameters": pso_res.parameters,
                "aco_score": path.score,
                "pso_improvement": pso_res.improvement,
                "iterations": pso_res.iterations,
                "provenance": path.provenance,
                "embedding": emb,
            })
        return {
            "query": query,
            "candidates": refined,
            "count": len(refined),
            "version": "0.2-async",
        }
