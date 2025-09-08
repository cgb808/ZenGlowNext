"""Build consolidated family fine-tune datasets + manifest.

Outputs (default ./datasets/family):
  instruction.jsonl    # instruction -> output pairs
  conversations.jsonl  # multi-turn chat samples (messages array)
  all.jsonl            # concatenated (instruction first, then conversations)
  manifest.json        # counts + sha256 digests

Usage:
  python scripts/build_family_dataset.py --out datasets/family \
      --conversation-weights artifact_retrieval=2,follow_up=1
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys, tempfile
from typing import Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.family.context import ensure_seed, FAMILY_STORE  # noqa: E402
import scripts.export_family_conversations as convo  # noqa: E402


def sha256_path(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


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


def generate_instruction(path: pathlib.Path):
    with path.open('w', encoding='utf-8') as w:
        # Artifacts
        for art in FAMILY_STORE.list_artifacts(limit=1000):
            prompt = f"Retrieve {art['kind']} titled '{art['title']}' for entity {art['entity_id']}"
            target = {"entity_id": art["entity_id"], "kind": art["kind"], "title": art["title"], "tags": art.get("tags", [])}
            json.dump({"instruction": prompt, "output": target, "meta": {"source": "artifact"}}, w)
            w.write('\n')
        # Health metrics
        for pid, buckets in getattr(FAMILY_STORE, "_buckets", {}).items():  # type: ignore[attr-defined]
            metrics = buckets.get("health", [])
            if metrics:
                latest = metrics[-1]
                prompt = f"What is the latest {latest['metric']} for {pid}?"
                answer = f"{latest['value']}{latest.get('unit','')}"
                json.dump({"instruction": prompt, "output": answer, "meta": {"source": "health_metric"}}, w)
                w.write('\n')


def generate_conversations(path: pathlib.Path, weights: Dict[str, int]):
    with path.open('w', encoding='utf-8') as w:
        for gen in convo.GENERATORS:
            for sample in gen():
                scenario = sample.get('meta', {}).get('scenario', '')
                reps = weights.get(scenario, 1)
                for _ in range(reps):
                    json.dump(sample, w)
                    w.write('\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='datasets/family')
    ap.add_argument('--conversation-weights', help='scenario=weight,... oversampling spec')
    args = ap.parse_args()

    ensure_seed()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    weights = parse_weights(args.conversation_weights)

    instruction_path = out_dir / 'instruction.jsonl'
    conversations_path = out_dir / 'conversations.jsonl'
    all_path = out_dir / 'all.jsonl'

    generate_instruction(instruction_path)
    generate_conversations(conversations_path, weights)

    # Concatenate
    with all_path.open('w', encoding='utf-8') as w_all:
        for p in (instruction_path, conversations_path):
            with p.open('r', encoding='utf-8') as r:
                for line in r:
                    w_all.write(line)

    manifest = {
        "files": {
            "instruction.jsonl": {"sha256": sha256_path(instruction_path), "lines": sum(1 for _ in instruction_path.open())},
            "conversations.jsonl": {"sha256": sha256_path(conversations_path), "lines": sum(1 for _ in conversations_path.open())},
            "all.jsonl": {"sha256": sha256_path(all_path), "lines": sum(1 for _ in all_path.open())},
        },
        "schema": {
            "instruction": {"fields": ["instruction", "output", "meta"]},
            "conversation": {"fields": ["messages", "meta"], "message_format": {"role": "system|user|assistant", "content": "string"}},
        },
        "meta": {"source": "family_context", "version": 1}
    }
    with (out_dir / 'manifest.json').open('w', encoding='utf-8') as m:
        json.dump(manifest, m, indent=2)

    print(json.dumps({"built": str(out_dir), "files": list(manifest['files'].keys())}))
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
