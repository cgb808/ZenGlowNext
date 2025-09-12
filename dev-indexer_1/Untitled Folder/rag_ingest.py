#!/usr/bin/env python
"""Batch ingest for RAG doc embeddings.
Usage:
  python scripts/rag_ingest.py --source docs --file path/to/file.txt
  python scripts/rag_ingest.py --source guide --glob 'docs/**/*.md'

Splits text into ~800 char chunks, embeds via local /model/embed endpoint, inserts into Postgres doc_embeddings.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
from typing import List, Set, Tuple

import psycopg  # v3
import requests

EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")
DSN = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
CHUNK_SIZE = int(os.getenv("INGEST_CHUNK_SIZE", "800"))
OVERLAP = int(os.getenv("INGEST_OVERLAP", "80"))
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))  # schema vector dimension


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk_text(txt: str) -> List[str]:
    txt = txt.replace("\r", "")
    chunks: List[str] = []
    n = len(txt)
    start = 0
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        seg = txt[start:end].strip()
        if seg:
            chunks.append(seg)
        # If we've reached the end, stop (prevents infinite loop when end==n)
        if end == n:
            break
        # Move window with overlap
        start = end - OVERLAP
        if start < 0:
            start = 0
    return chunks


def embed(chunks: List[str]) -> List[List[float]]:
    # Test / CI fast path: avoid network if EMBED_DUMMY=1 (returns fixed-dim zeros)
    if os.getenv("EMBED_DUMMY") == "1":  # lightweight mode
        return [[0.0] * EMBED_DIM for _ in chunks]
    r = requests.post(
        EMBED_ENDPOINT,
        json={"texts": chunks},
        timeout=int(os.getenv("EMBED_TIMEOUT", "20")),
    )
    r.raise_for_status()
    data = r.json()
    return data["embeddings"]


def insert(rows):  # legacy path not currently used (kept for backward compat)
    if os.getenv("INGEST_NO_DB") == "1":
        return
    if not DSN:
        raise SystemExit("DATABASE_URL / SUPABASE_DB_URL not set")
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO doc_embeddings (source, chunk, embedding, batch_tag, content_hash, metadata) VALUES (%s, %s, %s::vector, %s, %s, %s)",
                rows,
            )


def _hash_chunk(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _simple_clarifying_questions(text: str, n: int) -> List[str]:
    """Heuristic placeholder clarifying question generator.
    Extract capitalized terms / simple noun-ish tokens and form questions.
    Replace with model-based generation later.
    """
    tokens = re.findall(r"[A-Z][a-zA-Z]{3,}\b", text)[:10]
    dedup: List[str] = []
    seen: Set[str] = set()
    for t in tokens:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            dedup.append(t)
    questions: List[str] = []
    for t in dedup[:n]:
        questions.append(f"What is the significance of {t} in this context?")
    while len(questions) < n:
        questions.append("What additional context would clarify this section?")
    return questions[:n]


def _llm_clarifying_questions(text: str, n: int, model_name: str) -> List[str]:
    """Optional LLM-based clarifying question generator.
    Uses CLARIFYING_LLM_ENDPOINT (POST json {text, n, model}) -> {questions: [...]}.
    Falls back to heuristic if endpoint unset or error.
    """
    endpoint = os.getenv("CLARIFYING_LLM_ENDPOINT")
    if not endpoint:
        return _simple_clarifying_questions(text, n)
    try:
        r = requests.post(
            endpoint,
            json={"text": text, "n": n, "model": model_name},
            timeout=int(os.getenv("CLARIFYING_LLM_TIMEOUT", "25")),
        )
        r.raise_for_status()
        data = r.json()
        qs = data.get("questions") or []
        if not isinstance(qs, list) or not qs:
            return _simple_clarifying_questions(text, n)
        qs = [str(q).strip() for q in qs if isinstance(q, str) and q.strip()]
        if len(qs) < n:
            qs.extend(_simple_clarifying_questions(text, n - len(qs)))
        return qs[:n]
    except Exception as e:  # noqa: BLE001
        print(f"[clarify] llm_generation_error fallback -> heuristic: {e}")
        return _simple_clarifying_questions(text, n)


def _generate_clarifying_questions(
    text: str, n: int, model_name: str, generator: str
) -> List[str]:
    if generator == "llm":
        return _llm_clarifying_questions(text, n, model_name)
    return _simple_clarifying_questions(text, n)


def _score_chunk_for_clarification(text: str) -> int:
    """Heuristic priority score 1-9 for a chunk's need for clarification.

    Signals (additive, then bounded):
      - Pronoun / referential ambiguity early in text
      - Acronyms (ALLCAPS tokens)
      - Count of distinct capitalized entities (Proper nouns / concepts)
      - Presence of TODO / FIXME / TBD markers
      - Medium/long length (more surface for ambiguity)
      - Mixed numeric + unit patterns (e.g., 32ms, 5GB)
    """
    score = 0
    lower = text.lower()
    # Early ambiguous pronouns (first 160 chars)
    early_window = lower[:160]
    pronouns = re.findall(r"\b(this|that|these|those|it)\b", early_window)
    if pronouns:
        score += min(2, len(pronouns))  # cap influence
    # Acronyms
    acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
    if acronyms:
        score += min(3, len(set(acronyms)) // 2 + 1)
    # Capitalized entities (likely proper nouns / concepts)
    entities = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
    if len(entities) > 8:
        score += 3
    elif len(entities) > 4:
        score += 2
    elif len(entities) > 2:
        score += 1
    # TODO / FIXME markers
    if any(k in lower for k in ("todo", "fixme", "tbd")):
        score += 2
    # Numeric+unit complexity
    if re.search(r"\b\d+(ms|gb|mb|%|s|sec|secs|minutes|hrs|x)\b", lower):
        score += 1
    # Length weighting
    length = len(text)
    if length > 1800:
        score += (
            1  # very long: modest bump (may be broad context, not always ambiguous)
        )
    elif length > 1200:
        score += 3
    elif length > 600:
        score += 2
    elif length > 300:
        score += 1
    # Non-zero safety floor
    if score <= 0:
        score = 1
    # Bound 1..9
    return max(1, min(9, score))


def _insert_clarifying(
    chunk_rows: List[Tuple[int, str]],
    n: int,
    model_name: str,
    batch_tag: str,
    priority_mode: str = "fixed",
    fixed_priority: int = 5,
    generator: str = "heuristic",
):
    """Insert clarifying questions for provided (chunk_id, chunk_text) rows.
    priority_mode: 'fixed' or 'heuristic'.
    """
    if n <= 0:
        return 0
    if not DSN:
        print("[clarify] DATABASE_URL not set; skipping clarifying questions")
        return 0
    out_records = []
    for cid, text in chunk_rows:
        if priority_mode == "heuristic":
            priority = _score_chunk_for_clarification(text)
        else:
            priority = fixed_priority
        qs = _generate_clarifying_questions(text, n, model_name, generator)
        meta = {
            "generator": model_name,
            "batch_tag": batch_tag,
            "priority_mode": priority_mode,
            "gen_mode": generator,
        }
        for q in qs:
            out_records.append((cid, q, priority, json.dumps(meta)))
    if not out_records:
        return 0
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunk_clarifying_questions (chunk_id, question, priority, metadata) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                out_records,
            )
    print(
        f"[clarify] inserted {len(out_records)} clarifying questions (mode={priority_mode})"
    )
    return len(out_records)


def process(
    paths: List[str],
    source: str,
    batch_tag: str,
    gen_clarifying: int = 0,
    clarifying_model: str | None = None,
    clarifying_priority_mode: str = "fixed",
    clarifying_fixed_priority: int = 5,
    clarifying_generator: str = "heuristic",
):
    dedupe: Set[str] = set()
    all_rows = []
    for p in paths:
        txt = read_text(p)
        chunks = chunk_text(txt)
        if not chunks:
            continue
        embs = embed(chunks)
        for c, e in zip(chunks, embs):
            chash = _hash_chunk(c)
            if chash in dedupe and os.getenv("ENABLE_DEDUPE", "1") == "1":
                continue
            dedupe.add(chash)
            metadata = {"content_hash": chash, "source_path": p}
            all_rows.append((source, c, e, batch_tag, chash, json.dumps(metadata)))
    if not all_rows:
        return 0
    if os.getenv("INGEST_NO_DB") == "1":
        return len(all_rows)
    if not DSN:
        raise SystemExit("DATABASE_URL / SUPABASE_DB_URL not set")
    inserted_chunks: List[Tuple[int, str]] = []  # (id, chunk_text) for clarifying
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # Insert rows returning ids one-by-one (could batch with COPY later)
            insert_sql = "INSERT INTO doc_embeddings (source, chunk, embedding, batch_tag, content_hash, metadata) VALUES (%s,%s,%s::vector,%s,%s,%s) RETURNING id, chunk"
            for row in all_rows:
                cur.execute(insert_sql, row)
                fetched = cur.fetchone()
                if fetched:
                    rid, ctext = fetched
                    inserted_chunks.append((rid, ctext))
        if gen_clarifying > 0:
            _insert_clarifying(
                inserted_chunks,
                gen_clarifying,
                clarifying_model or "heuristic_v0",
                batch_tag,
                priority_mode=clarifying_priority_mode,
                fixed_priority=clarifying_fixed_priority,
                generator=clarifying_generator,
            )
    return len(all_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--file")
    ap.add_argument("--glob")
    ap.add_argument("--batch-tag", default="manual_ingest")
    ap.add_argument(
        "--gen-clarifying",
        type=int,
        default=int(os.getenv("GEN_CLARIFYING", "0")),
        help="Generate N clarifying questions per chunk (heuristic)",
    )
    ap.add_argument(
        "--clarifying-model",
        default=os.getenv("CLARIFYING_MODEL"),
        help="Model name tag for clarifying questions (metadata)",
    )
    ap.add_argument(
        "--clarifying-priority-mode",
        choices=["fixed", "heuristic"],
        default=os.getenv("CLARIFYING_PRIORITY_MODE", "heuristic"),
        help="Priority assignment strategy for clarifying questions",
    )
    ap.add_argument(
        "--clarifying-fixed-priority",
        type=int,
        default=int(os.getenv("CLARIFYING_FIXED_PRIORITY", "5")),
        help="Fixed priority value when mode=fixed",
    )
    ap.add_argument(
        "--clarifying-generator",
        choices=["heuristic", "llm"],
        default=os.getenv("CLARIFYING_GENERATOR", "heuristic"),
        help="Clarifying question generator backend",
    )
    args = ap.parse_args()
    paths = []
    if args.file:
        paths.append(args.file)
    if args.glob:
        paths.extend(glob.glob(args.glob, recursive=True))
    if not paths:
        raise SystemExit("Provide --file or --glob")
    total = process(
        paths,
        args.source,
        args.batch_tag,
        gen_clarifying=args.gen_clarifying,
        clarifying_model=args.clarifying_model,
        clarifying_priority_mode=args.clarifying_priority_mode,
        clarifying_fixed_priority=args.clarifying_fixed_priority,
        clarifying_generator=args.clarifying_generator,
    )
    print(f"Ingested rows: {total}")


if __name__ == "__main__":
    main()
