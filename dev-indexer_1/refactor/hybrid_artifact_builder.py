#!/usr/bin/env python3
"""Build hybrid dataset artifacts: copy JSONL, create msgpack, emit metadata & optional schema.
"""
from __future__ import annotations
import argparse, json, msgpack, hashlib
from pathlib import Path


def sha256(s: bytes) -> str:
    import hashlib
    h = hashlib.sha256(); h.update(s); return h.hexdigest()


def main():  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--emit-jsonl', action='store_true')
    ap.add_argument('--emit-msgpack', action='store_true')
    ap.add_argument('--weaviate-schema-out')
    args = ap.parse_args()
    src = Path(args.dataset)
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dataset_records = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    meta = {
        'records': len(dataset_records),
        'categories': {k: sum(1 for r in dataset_records if r.get('category') == k) for k in ('pure','math')},
    }
    (out_dir / f"{args.prefix}_metadata.json").write_text(json.dumps(meta, indent=2))
    base_jsonl = out_dir / f"{args.prefix}_dataset.jsonl"
    if args.emit_jsonl:
        base_jsonl.write_text('\n'.join(json.dumps(r) for r in dataset_records) + '\n')
    if args.emit_msgpack:
        mp_path = out_dir / f"{args.prefix}_dataset.msgpack"
        with mp_path.open('wb') as fh:
            msgpack.pack({'version':1,'count':len(dataset_records),'records':dataset_records}, fh)
    # Schema (placeholder if not present)
    if args.weaviate_schema_out:
        # If a root-level hybrid_schema.json already exists, copy path into out_dir
        root_schema = Path('hybrid_schema.json')
        target = out_dir / 'hybrid_schema.json'
        if root_schema.exists():
            target.write_text(root_schema.read_text())
        else:
            target.write_text(json.dumps({'classes': []}, indent=2))
    print(f"[hybrid-artifacts] meta={meta}")


if __name__ == '__main__':
    main()
