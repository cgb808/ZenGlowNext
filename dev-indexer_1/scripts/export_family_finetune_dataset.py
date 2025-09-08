"""Export family context artifacts + buckets into a fine-tuning ready JSONL set.

Usage (after virtualenv activation):
    python scripts/export_family_finetune_dataset.py > family_dataset.jsonl

Current strategy:
- Each artifact yields one training example with a synthetic instruction asking
  for a summary or retrieval of that artifact based on tags.
- Health metrics produce Q&A style pairs ("What is latest <metric> for <name>?").

Future:
- Integrate conversational turns referencing timeline events.
"""
from __future__ import annotations
import json, sys, pathlib

# Ensure project root on path when executed directly
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.family.context import ensure_seed, FAMILY_STORE

def main() -> int:
    ensure_seed()
    # Artifact-based examples
    for art in FAMILY_STORE.list_artifacts(limit=1000):
        prompt = f"Retrieve {art['kind']} titled '{art['title']}' for entity {art['entity_id']}"
        target = {
            "entity_id": art["entity_id"],
            "kind": art["kind"],
            "title": art["title"],
            "tags": art.get("tags", []),
        }
        json.dump({"instruction": prompt, "output": target, "meta": {"source": "artifact"}}, sys.stdout)
        sys.stdout.write("\n")
    # Health metrics
    for pid, buckets in FAMILY_STORE._buckets.items():  # type: ignore[attr-defined]
        metrics = buckets.get("health", [])
        if metrics:
            latest = metrics[-1]
            prompt = f"What is the latest {latest['metric']} for {pid}?"
            answer = f"{latest['value']}{latest.get('unit','')}"
            json.dump({"instruction": prompt, "output": answer, "meta": {"source": "health_metric"}}, sys.stdout)
            sys.stdout.write("\n")
    return 0

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
