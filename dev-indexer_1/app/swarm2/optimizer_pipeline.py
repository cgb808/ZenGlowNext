from __future__ import annotations
from typing import Any, Dict, List
import asyncio

from .optimizers.aco import ant_colony_optimize
from .optimizers.pso import particle_swarm_optimize

class OptimizerPipeline:
    async def optimize(self, query: str) -> Dict[str, Any]:
        aco_task = asyncio.create_task(self._run_aco(query))
        pso_task = asyncio.create_task(self._run_pso(query))
        aco_res, pso_res = await asyncio.gather(aco_task, pso_task)
        # Combine results; simplistic merge for now
        candidates: List[Dict[str, Any]] = []
        for item in aco_res.get("candidates", []):
            candidates.append(item)
        for item in pso_res.get("candidates", []):
            candidates.append(item)
        return {"candidates": candidates}

    async def _run_aco(self, query: str) -> Dict[str, Any]:
        return await ant_colony_optimize(query)

    async def _run_pso(self, query: str) -> Dict[str, Any]:
        return await particle_swarm_optimize(query)
