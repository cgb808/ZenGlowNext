"""Unified dataset exporter for instruction and conversation samples.

Usage examples:
  python scripts/export_family_dataset.py --mode instruction > instr.jsonl
  python scripts/export_family_dataset.py --mode conversation --scenario-weights artifact_retrieval=2,follow_up=1 > convo.jsonl
  python scripts/export_family_dataset.py --mode all > all.jsonl

Scenario weighting duplicates samples (simple oversampling) for conversation.
"""
from __future__ import annotations
import argparse, json, sys, pathlib
from typing import Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.family.context import ensure_seed, FAMILY_STORE  # noqa: E402
import scripts.export_family_conversations as convo  # type: ignore  # noqa: E402


def generate_instruction_samples():
    # Artifacts
    for art in FAMILY_STORE.list_artifacts(limit=1000):
        prompt = f"Retrieve {art['kind']} titled '{art['title']}' for entity {art['entity_id']}"
        target = {
            "entity_id": art["entity_id"],
            "kind": art["kind"],
            "title": art["title"],
            "tags": art.get("tags", []),
        }
        yield {"instruction": prompt, "output": target, "meta": {"source": "artifact"}}
    # Health metrics
    for pid, buckets in getattr(FAMILY_STORE, "_buckets", {}).items():  # type: ignore[attr-defined]
        metrics = buckets.get("health", [])
        if metrics:
            latest = metrics[-1]
            prompt = f"What is the latest {latest['metric']} for {pid}?"
            answer = f"{latest['value']}{latest.get('unit','')}"
            yield {"instruction": prompt, "output": answer, "meta": {"source": "health_metric"}}


def parse_weights(spec: str | None) -> Dict[str, int]:
    if not spec:
        return {}
    out: Dict[str, int] = {}
    for part in spec.split(','):
        if not part:
            continue
        k, _, v = part.partition('=')
        try:
            out[k.strip()] = max(1, int(v))
        except ValueError:
            out[k.strip()] = 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['instruction','conversation','all'], default='all')
    ap.add_argument('--scenario-weights', help='Comma list scenario=weight for conversation oversampling')
    args = ap.parse_args()

    ensure_seed()
    weights = parse_weights(args.scenario_weights)
    count = 0

    if args.mode in ('instruction','all'):
        for item in generate_instruction_samples():
            json.dump(item, sys.stdout); sys.stdout.write('\n'); count += 1

    if args.mode in ('conversation','all'):
        for gen in convo.GENERATORS:
            for sample in gen():
                scenario = sample.get('meta', {}).get('scenario','')
                w = weights.get(scenario, 1)
                for _ in range(w):
                    json.dump(sample, sys.stdout); sys.stdout.write('\n'); count += 1

    return 0 if count else 1

if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
