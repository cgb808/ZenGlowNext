#!/usr/bin/env python3
"""Generate synthetic RAG usage examples (for training answer style / citation handling)."""
from __future__ import annotations
import argparse, json, random, msgpack, time
from pathlib import Path


TEMPLATES = [
    ("What is the benefit of spaced repetition?", "Spaced repetition improves long-term retention by revisiting material just before it would be forgotten."),
    ("Explain the distributive property.", "It states a(b + c) = ab + ac, allowing expansion of expressions."),
    ("How do you factor x^2 + 5x + 6?", "Find two numbers multiplying to 6 and summing to 5: (x+2)(x+3)."),
]


def main():  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--total', type=int, default=50)
    args = ap.parse_args()
    rnd = random.Random(7)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    recs = []
    for i in range(args.total):
        q, a = rnd.choice(TEMPLATES)
        recs.append({'question': q, 'answer': a, 'id': i, 'citations': []})
    out.write_text('\n'.join(json.dumps(r) for r in recs) + '\n')
    # MsgPack sibling
    mp = Path(str(out).replace('.jsonl', '.msgpack'))
    with mp.open('wb') as fh:
        msgpack.pack({'version':1,'count':len(recs),'records':recs,'created_at':time.time()}, fh)
    print(f"[rag-usage] wrote {len(recs)} examples -> {out}")


if __name__ == '__main__':
    main()
