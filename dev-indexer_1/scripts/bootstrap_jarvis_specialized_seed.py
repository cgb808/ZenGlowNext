#!/usr/bin/env python3
"""Bootstrap Specialized Jarvis Dataset (SLOW POPULATION)

Generates a very small synthetic seed set for each gap bucket in
`jarvis_specialized_v1.yaml` (or another compatible manifest) so that
the pipeline can be validated before large-scale synthesis.

Defaults: 3 rows per bucket (configurable) to respect a "populate slow" strategy.

Only standard library is used. Content is schematic but structured to match
required meta + selective artifacts. Later, dedicated high-fidelity generators
should replace these placeholder routines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List


RNG = random.Random(20250903)


def load_yaml_minimal(path: str) -> Dict[str, Any]:
    """Very small YAML subset loader (assumes simple key: value / nesting) to avoid PyYAML dependency.
    We only need buckets + staging_dir.
    """
    data: Dict[str, Any] = {}
    stack: List[Dict[str, Any]] = [data]
    indent_stack = [0]

    def current():
        return stack[-1]

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            while indent < indent_stack[-1]:
                stack.pop()
                indent_stack.pop()
            if ":" in line:
                key, val = line.lstrip().split(":", 1)
                key = key.strip()
                val = val.strip()
                if val == "":
                    # Start new mapping
                    new_map: Dict[str, Any] = {}
                    current()[key] = new_map
                    stack.append(new_map)
                    indent_stack.append(indent + 2)
                else:
                    # Simple scalar
                    # Try to coerce ints/bools
                    if val.lower() in ("true", "false"):
                        coerced: Any = val.lower() == "true"
                    else:
                        try:
                            coerced = int(val)
                        except ValueError:
                            coerced = val
                    current()[key] = coerced
            elif line.lstrip().startswith("-"):
                # We only minimally support lists of scalars here; not needed for buckets.
                # Skip for this bootstrap.
                continue
    return data


def deterministic_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_meta(bucket: str, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = {
        "interaction_type": bucket,
        "mood_state": RNG.choice(["neutral", "calm", "engaged", "supportive"]),
        "time_context": datetime.utcnow().strftime("%Y-%m-%dT%H:00Z"),
        "holiday_flag": False,
        "calendar_event": RNG.choice(["none", "weekly_review", "project_checkpoint"]),
        "agents_involved": ["phi3", "mistral_7b"],
        "primary_agent": "phi3",
        "tools_invoked": [],
        "reasoning_style": RNG.choice(["direct", "reflective", "chain"]),
        "safety_tier": RNG.choice(["baseline", "contextual"]),
        "user_intent_class": RNG.choice(["inquire", "plan", "revise"]),
        "outcome_type": RNG.choice(["answer", "plan", "correction"]),
    }
    if overrides:
        base.update(overrides)
    return base


def artifact_for_bucket(bucket: str) -> Dict[str, Any]:
    if bucket.startswith("tooling_whiteboard"):
        return {
            "whiteboard_state": [
                {"cell": 1, "content": "Goal: outline solution", "change_type": "add"},
                {"cell": 1, "content": "Refine: add validation step", "change_type": "update"},
            ],
            "plan_tree": {
                "goal": "deliver answer",
                "steps": [
                    {"id": "s1", "title": "Understand", "rationale": "Clarify user need"},
                    {"id": "s2", "title": "Plan", "rationale": "Outline approach"},
                ],
            },
        }
    if bucket.startswith("tooling_rag"):
        return {
            "retrieval_chunks": [
                {"id": "doc1", "source": "kb://design/principles", "text": "Principle: clarity first", "relevance_score": 0.91},
            ],
            "source_citations": ["doc1"],
            "grounding_confidence": 0.87,
        }
    if bucket.startswith("tooling_code_review"):
        return {
            "error_diff": {
                "before": "def add(a,b):return a-b",
                "after": "def add(a, b):\n    return a + b",
                "explanation": "Incorrect operator; replaced '-' with '+' and formatted",
            }
        }
    if bucket.startswith("tooling_asr_alignment"):
        return {
            "transcript_raw": "uh schedule standup tomorrow at 9?",
            "transcript_clean": "Schedule standup tomorrow at 09:00.",
            "alignment_map": [
                {"raw_span": [0, 2], "clean_span": [0, 0], "note": "filler removed"}
            ],
        }
    if bucket.startswith("multi_agent_conflict"):
        return {
            "arbitration_log": [
                {"agent": "mistral_7b", "proposal": "Use structured outline."},
                {"agent": "phi3", "proposal": "Give concise answer."},
                {"resolution": "Provide concise answer with optional outline summary."},
            ]
        }
    if bucket.startswith("multi_agent_tool_dispatch"):
        return {
            "arbitration_log": [
                {"agent": "number5", "proposal": "Generate whiteboard state."},
                {"agent": "bge", "proposal": "Retrieve grounding docs."},
            ],
            "tools_invoked": ["whiteboard.number5", "embed.bge"],
        }
    if bucket.startswith("error_correction"):
        return {
            "error_diff": {
                "before": "User intent misread as X",
                "after": "Corrected interpretation Y",
                "explanation": "Clarified ambiguous term 'spec'.",
            },
            "self_review": [
                {"risk": "Ambiguity", "severity": "low", "mitigation": "Asked clarifying question."}
            ],
        }
    if bucket.startswith("deep_reasoning_socratic"):
        return {
            "plan_tree": {
                "goal": "arrive at synthesis",
                "steps": [
                    {"id": "q1", "title": "Probe", "rationale": "Elicit user's implicit assumptions"},
                    {"id": "q2", "title": "Refine", "rationale": "Narrow conceptual space"},
                ],
            }
        }
    if bucket.startswith("safety_alignment_refusals"):
        return {
            "safe_alternative": {
                "reason": "Disallowed request context",
                "offered_path": "Provide high-level guidance without sensitive details",
            }
        }
    return {}


def synth_example(bucket: str, idx: int) -> Dict[str, Any]:
    user_prompt = f"[{bucket.upper()}] Please help with a conceptual question variant {idx}."[:200]
    if "contextual_mood_greetings" in bucket:
        user_prompt = "User initiates session; expects warm adaptive greeting."  # override
    assistant = f"Response for {bucket} case {idx}: high-signal illustrative answer with no math."
    meta_overrides: Dict[str, Any] = {}
    if "greetings" in bucket:
        meta_overrides["mood_state"] = RNG.choice(["uplifted", "calm", "professional"]) 
    if "holiday" in bucket:
        meta_overrides["holiday_flag"] = True
        meta_overrides["calendar_event"] = RNG.choice(["new_year", "solstice", "regional_holiday"])
    if bucket.startswith("tooling_asr_alignment"):
        meta_overrides["agents_involved"] = ["whispercpp", "phi3"]
        meta_overrides["primary_agent"] = "phi3"
    if bucket.startswith("multi_agent"):
        meta_overrides["agents_involved"] = ["mistral_7b", "phi3", "number5"]
        meta_overrides["primary_agent"] = "mistral_7b"
    meta = build_meta(bucket, overrides=meta_overrides)
    artifacts = artifact_for_bucket(bucket)
    record = {
        "id": f"{bucket}__{idx}",
        "timestamp": now_iso(),
        "instruction": user_prompt,
        "response": assistant,
        "metadata": meta,
    }
    if artifacts:
        record["artifacts"] = artifacts
    # compute content hash
    content_hash = deterministic_hash(record["instruction"] + "||" + record["response"])
    record["content_hash"] = content_hash
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="Path to specialized manifest YAML")
    ap.add_argument("--rows-per-bucket", type=int, default=3, help="Small seed rows per gap bucket")
    ap.add_argument("--out-dir", default=None, help="Override staging dir")
    args = ap.parse_args()

    manifest = load_yaml_minimal(args.manifest)
    buckets = manifest.get("buckets", {})
    staging_dir = (
        args.out_dir
        if args.out_dir
        else manifest.get("output", {}).get("staging_dir", "fine_tuning/datasets/processed/jarvis_specialized_v1")
    )
    os.makedirs(staging_dir, exist_ok=True)

    summary = []
    for bucket_name, cfg in buckets.items():
        if not isinstance(cfg, dict):
            continue
        if not cfg.get("gap", False):
            # Skip populated buckets if any; this manifest sets all as gaps.
            continue
        path = os.path.join(staging_dir, f"{bucket_name}.jsonl")
        count = args.rows_per_bucket
        with open(path, "w", encoding="utf-8") as f:
            for i in range(count):
                rec = synth_example(bucket_name, i + 1)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        summary.append((bucket_name, count, path))

    total = sum(c for _, c, _ in summary)
    print(f"✅ Generated seed data for {len(summary)} buckets; total rows={total}")
    for name, cnt, path in summary:
        print(f"  - {name}: {cnt} -> {path}")
    print("Done. Scale-up scripts can later replace/append these seeds.")


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        sys.exit(130)
