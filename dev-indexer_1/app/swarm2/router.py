from fastapi import APIRouter, Depends
from typing import Optional

from .event_logger import log_event, compute_query_hash, compute_path_hash

from .selectors.partition_scheduler import PartitionScheduler, build_default_scheduler
from .rag_client import HistoricalRagClient
from .ingestion import get_ingestion
from .optimizer_pipeline import OptimizerPipeline

# For now fixed small partition count; could be env-driven later
_scheduler: PartitionScheduler = build_default_scheduler(
    partitions=5,
    predictive_hook=lambda pid, feats: get_ingestion().predictive_hook(pid, feats),
    rag_client=HistoricalRagClient(),
)
_optimizer_pipeline = OptimizerPipeline()

router = APIRouter(prefix="/swarm", tags=["swarm2"])


def get_scheduler() -> PartitionScheduler:
    return _scheduler


@router.get("/snapshot")
async def snapshot(scheduler: PartitionScheduler = Depends(get_scheduler)):
    """Lightweight snapshot of current partitions & metrics."""
    return scheduler.snapshot()


@router.post("/route")
async def route(
    session_id: Optional[str] = None,
    user_hash: Optional[str] = None,
    scheduler: PartitionScheduler = Depends(get_scheduler),
):
    """Request partition assignment.

    Returns partition id and swarm type (PRIMARY/EXPLORER).
    """
    stype, pid = scheduler.route()
    payload = {"partition_id": pid, "swarm_type": stype}
    log_event(
        event_type="swarm_route",
        session_id=session_id,
        user_hash=user_hash,
        partition_id=pid,
        swarm_type=stype,
    )
    return payload


@router.post("/feedback")
async def feedback(
    partition_id: int,
    success: bool,
    latency_ms: float,
    session_id: Optional[str] = None,
    user_hash: Optional[str] = None,
    scheduler: PartitionScheduler = Depends(get_scheduler),
):
    """Provide execution feedback so scheduler can update telemetry."""
    # Ingest first so predictive hook sees the current event in recent deque
    try:
        get_ingestion().ingest_feedback(partition_id, success=success, latency_ms=latency_ms)  # type: ignore
    except Exception:
        pass
    scheduler.feedback(partition_id, success=success, latency_ms=latency_ms)
    log_event(
        event_type="swarm_feedback",
        session_id=session_id,
        user_hash=user_hash,
        partition_id=partition_id,
        success=success,
        latency_ms=latency_ms,
    )
    return {"status": "ok"}


@router.post("/optimize")
async def optimize(
    query: str,
    session_id: Optional[str] = None,
    user_hash: Optional[str] = None,
):
    """Run ACO (explore) + PSO (exploit) pipeline for a given query.

    Returns candidate optimized factor sets with parameters.
    """
    result = await _optimizer_pipeline.optimize(query)
    qh = compute_query_hash(query)
    # Log each candidate with path hash
    for cand in result.get("candidates", []):
        factors = cand.get("factors") or []
        params = cand.get("parameters") or {}
        ph = compute_path_hash(factors, params)
        embedding = cand.get("embedding")
        log_event(
            event_type="swarm_optimize",
            session_id=session_id,
            user_hash=user_hash,
            query_text=query,
            query_hash=qh,
            factors=factors,
            parameters=params,
            path_hash=ph,
            event_embedding=embedding,
        )
    return result
