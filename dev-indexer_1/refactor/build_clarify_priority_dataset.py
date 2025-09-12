#!/usr/bin/env python
"""Build Clarifying Priority Weak Label Dataset

Generates a training dataset for a tiny priority model by:
  * Selecting chunks from doc_embeddings (or reading a JSONL/glob fallback later)
  * Computing heuristic priority (re-using logic from rag_ingest._score_chunk_for_clarification)
  * Extracting feature vector via clarify_priority_features.extract_features
  * Writing JSONL rows: {chunk_id, priority_label, features, text_hash, source, meta}

Environment / CLI:
  DATABASE_URL / SUPABASE_DB_URL must be set unless --input-jsonl used (future).
  --limit N to cap rows.
  --min-chars / --max-chars to filter extreme lengths.
  --out path/to/file.jsonl (default: data/clarify_priority/weak_priority_dataset.jsonl)
  --seed for reproducible shuffle.

Future Enhancements:
    - Accept external chunk text source
    - Pairwise dataset generation
    - Feature caching
    - Augmented variants (implemented)
"""
from __future__ import annotations
import os, sys, json, argparse, hashlib, random
import psycopg  # v3
from typing import Dict, Any, List

DSN = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _score_chunk_for_clarification(text: str) -> int:
    # Minimal duplicate of rag_ingest version (avoid import side effects) — keep in sync.
    import re
    score = 0
    lower = text.lower()
    early_window = lower[:160]
    pronouns = re.findall(r"\b(this|that|these|those|it)\b", early_window)
    if pronouns:
        score += min(2, len(pronouns))
    acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
    if acronyms:
        score += min(3, len(set(acronyms)) // 2 + 1)
    entities = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
    if len(entities) > 8:
        score += 3
    elif len(entities) > 4:
        score += 2
    elif len(entities) > 2:
        score += 1
    if any(k in lower for k in ("todo", "fixme", "tbd")):
        score += 2
    if re.search(r"\b\d+(ms|gb|mb|%|s|sec|secs|minutes|hrs|x)\b", lower):
        score += 1
    length = len(text)
    if length > 1800:
        score += 1
    elif length > 1200:
        score += 3
    elif length > 600:
        score += 2
    elif length > 300:
        score += 1
    if score <= 0:
        score = 1
    return max(1, min(9, score))


def fetch_chunks(limit: int | None, min_chars: int, max_chars: int) -> List[dict]:
    if not DSN:
        raise SystemExit("DATABASE_URL / SUPABASE_DB_URL not set")
    q = [
        "SELECT id, chunk, source, metadata::text AS metadata FROM doc_embeddings",
        "WHERE length(chunk) BETWEEN %s AND %s",
    ]
    params: List[Any] = [min_chars, max_chars]
    if limit:
        q.append("LIMIT %s")
        params.append(limit)
    sql = "\n".join(q)
    rows: List[dict] = []
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for rid, chunk, source, metadata in cur.fetchall():
                rows.append({
                    "id": rid,
                    "chunk": chunk,
                    "source": source,
                    "metadata": metadata,
                })
    return rows


def _augment_text(text: str) -> list[tuple[str, str]]:
    """Produce lightweight augmented variants for contrastive weak supervision.
    Returns list of (variant_text, variant_type).
    """
    import re
    variants: list[tuple[str,str]] = []
    # Drop initial pronoun/demonstrative if present
    pronoun_drop = re.sub(r'^\b(This|That|It|These|Those)\b\s+', '', text, flags=re.IGNORECASE)
    if pronoun_drop != text and len(pronoun_drop) > 40:
        variants.append((pronoun_drop, 'pronoun_drop'))
    # Expand a couple acronyms with placeholder expansion
    def expand_acr(m):
        a = m.group(0)
        return f"{a} ({a.lower()} placeholder)"
    acronym_expand = re.sub(r'\b[A-Z]{2,5}\b', expand_acr, text, count=2)
    if acronym_expand != text and len(acronym_expand) < 5000:
        variants.append((acronym_expand, 'acronym_expand'))
    # Append hint sentence
    base = text if text.endswith('.') else text + '.'
    hint = base + ' Clarification: key terms are defined inline.'
    if len(hint) < 5000:
        variants.append((hint, 'hint_append'))
    return variants


def build(args):
    from app.rag.clarify_priority_features import extract_features
    rows = fetch_chunks(args.limit, args.min_chars, args.max_chars)
    if not rows:
        print("No rows selected")
        return 0
    random.Random(args.seed).shuffle(rows)
    out_path = args.out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    written = 0
    pair_f = None
    if args.pairwise_out:
        os.makedirs(os.path.dirname(args.pairwise_out), exist_ok=True)
        pair_f = open(args.pairwise_out, 'w', encoding='utf-8')
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            text = r["chunk"]
            priority = _score_chunk_for_clarification(text)
            feats, meta = extract_features(text)
            rec = {
                "chunk_id": r["id"],
                "priority_label": priority,
                "features": feats,
                "text_hash": _hash(text),
                "source": r.get("source"),
                "meta": {
                    "feature_meta": meta,
                    "raw_metadata": r.get("metadata"),
                    "heuristic_version": 1,
                },
            }
            f.write(json.dumps(rec) + "\n")
            written += 1
            # Augment & pairwise optional
            if args.augment:
                variants = _augment_text(text)
                for v_text, v_type in variants:
                    v_priority = _score_chunk_for_clarification(v_text)
                    v_feats, v_meta = extract_features(v_text)
                    v_rec = {
                        "chunk_id": r["id"],
                        "priority_label": v_priority,
                        "features": v_feats,
                        "text_hash": _hash(v_text),
                        "source": r.get("source"),
                        "meta": {
                            "feature_meta": v_meta,
                            "raw_metadata": r.get("metadata"),
                            "heuristic_version": 1,
                            "aug_type": v_type,
                        },
                    }
                    f.write(json.dumps(v_rec) + "\n")
                    written += 1
                    if pair_f:
                        pref = 'tie'
                        if rec["priority_label"] > v_rec["priority_label"]:
                            pref = 'anchor'
                        elif v_rec["priority_label"] > rec["priority_label"]:
                            pref = 'variant'
                        pair_f.write(json.dumps({
                            "anchor_hash": rec["text_hash"],
                            "variant_hash": v_rec["text_hash"],
                            "anchor_label": rec["priority_label"],
                            "variant_label": v_rec["priority_label"],
                            "preferred": pref,
                            "aug_type": v_type,
                        }) + "\n")
    print(f"[clarify-dataset] wrote {written} rows -> {out_path}")
    if pair_f:
        pair_f.close()
        print(f"[clarify-dataset] pairwise file -> {args.pairwise_out}")
    return written


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=int(os.getenv('CLARIFY_DATA_LIMIT','5000')))
    ap.add_argument('--min-chars', type=int, default=150)
    ap.add_argument('--max-chars', type=int, default=4000)
    ap.add_argument('--out', default=os.getenv('CLARIFY_DATA_OUT','data/clarify_priority/weak_priority_dataset.jsonl'))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--augment', action='store_true', help='Generate augmented contrastive variants')
    ap.add_argument('--pairwise-out', help='Optional pairwise JSONL output')
    return ap.parse_args()


if __name__ == '__main__':  # pragma: no cover
    args = parse_args()
    build(args)
