from __future__ import annotations
import math
from typing import List, Tuple, Dict

DEFAULT_THRESHOLDS = {
    "min_avg_logprob": -1.5,  # lower (more negative) => uncertain
    "max_entropy": 2.5,
    "min_top1_prob": 0.20,
}


def decide_action(metrics: Dict[str, float], thresholds: Dict[str, float] | None = None) -> str:
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if metrics.get("avg_logprob", 0) < th["min_avg_logprob"]:
        return "reflect"  # ask model to reason or retrieve context
    if metrics.get("entropy", 0) > th["max_entropy"]:
        return "retrieve"  # fallback to retrieval augmentation
    if metrics.get("top1_prob", 1) < th["min_top1_prob"]:
        return "abstain"
    return "proceed"


def gate_from_token_logprobs(tokens: List[Tuple[str, float]]) -> str:
    # simple helper usable before persistence
    if not tokens:
        return "abstain"
    avg_lp = sum(lp for _, lp in tokens) / len(tokens)
    top1_prob = math.exp(tokens[0][1])
    entropy = sum(abs(lp) for _, lp in tokens[:5]) / max(1, min(5, len(tokens)))  # crude proxy
    metrics = {"avg_logprob": avg_lp, "top1_prob": top1_prob, "entropy": entropy}
    return decide_action(metrics)
