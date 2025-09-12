#!/usr/bin/env python3
"""Domain adaptation fine-tune for BGE-small using sentence-transformers.

Input: JSONL pairs from bge_build_pairs.py
Each line: {anchor, positive, negatives[], meta{}}

We use MultipleNegativesRankingLoss for (anchor, positive) pairs and incorporate
negatives via in-batch + explicit hard negatives (concatenate).
"""
from __future__ import annotations
import argparse, json, math, os
from pathlib import Path
from typing import List

from sentence_transformers import SentenceTransformer, losses, models, InputExample
from torch.utils.data import DataLoader


def read_pairs(path: Path, max_neg: int) -> List[InputExample]:
    ex=[]
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                rec=json.loads(line)
            except Exception:
                continue
            anchor=rec.get('anchor'); pos=rec.get('positive')
            if not anchor or not pos: continue
            texts=[anchor, pos]
            negs = (rec.get('negatives') or [])[:max_neg]
            for n in negs:
                if isinstance(n,str) and n.strip():
                    texts.append(n)
            ex.append(InputExample(texts=texts))
    return ex


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--base-model', default='BAAI/bge-small-en-v1.5')
    ap.add_argument('--epochs', type=int, default=2)
    ap.add_argument('--batch-size', type=int, default=64)
    ap.add_argument('--lr', type=float, default=2e-5)
    ap.add_argument('--max-neg', type=int, default=2)
    ap.add_argument('--warmup-ratio', type=float, default=0.05)
    ap.add_argument('--scheduler', type=str, default='WarmupLinear', help='Scheduler: WarmupLinear|WarmupCosine|WarmupConstant|WarmupCosineWithHardRestarts|WarmupPoly')
    ap.add_argument('--output', required=True)
    args=ap.parse_args()

    pairs_path=Path(args.pairs)
    examples=read_pairs(pairs_path, args.max_neg)
    if not examples:
        raise SystemExit('No training examples found')

    model = SentenceTransformer(args.base_model, trust_remote_code=True)

    train_dl = DataLoader(examples, batch_size=args.batch_size, shuffle=True)
    loss = losses.MultipleNegativesRankingLoss(model)

    warmup_steps = math.ceil(len(train_dl) * args.epochs * args.warmup_ratio)
    model.fit(
        train_objectives=[(train_dl, loss)],
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        use_amp=True,
        scheduler=args.scheduler,
        optimizer_params={'lr': args.lr},
        output_path=args.output,
        save_best_model=True,
        checkpoint_path=None,
    )
    print(f"[bge-train] model saved -> {args.output}")

if __name__=='__main__':
    main()
