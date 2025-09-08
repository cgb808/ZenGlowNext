#!/usr/bin/env python
"""Export family artifact corpus JSONL for embedding training.

Output:
  datasets/family/artifact_corpus.jsonl  (one JSON object per artifact)
  datasets/family/artifact_tags_summary.json (tag frequencies + basic stats)

Schema per line (keys may expand later):
  artifact_id, entity_id, kind, title, text, tags, meta, grade_band,
  entity_roles, household_id, guardians, children, derived_features,
  split, source_ref

Text resolution strategy:
  1. If content_ref points to a readable file, read its contents as text (utf-8, max 32KB).
  2. Else synthesize from title + meta short summary.

Split: currently all 'train'. Add holdout logic later by modifying SPLIT_RATIO.

Safe to run multiple times (idempotent for current in-memory artifact set).
"""
from __future__ import annotations
import os, json, math, hashlib
from pathlib import Path
from typing import Any, Dict, List

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.family.context import FAMILY_STORE, ensure_seed  # type: ignore

MAX_FILE_BYTES = 32 * 1024  # 32KB safety cap
DATASET_DIR = Path("datasets/family")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSONL = DATASET_DIR / "artifact_corpus.jsonl"
TAGS_SUMMARY = DATASET_DIR / "artifact_tags_summary.json"
DEFAULT_SPLIT = "train"


def _read_content_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    # Accept plain paths or simple scheme prefix like content_ref://
    cleaned = ref.replace("content_ref://", "")
    p = Path(cleaned)
    if not p.exists() or not p.is_file():
        return None
    try:
        raw = p.read_bytes()[:MAX_FILE_BYTES]
        # naive binary guard: try utf-8
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _meta_snippet(meta: Dict[str, Any]) -> str:
    if not meta:
        return ""
    try:
        items = [f"{k}={v}" for k, v in list(meta.items())[:6]]
        return "; ".join(items)
    except Exception:
        return ""


def _token_count(text: str) -> int:
    return len(text.split()) if text else 0


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def build_corpus() -> Dict[str, Any]:
    ensure_seed()
    people = {p.id: p for p in FAMILY_STORE.list_people()}
    relationships = FAMILY_STORE._relationships  # internal (read-only usage)
    guardians_map: Dict[str, List[str]] = {}
    children_map: Dict[str, List[str]] = {}
    for r in relationships:
        guardians_map.setdefault(r.child_id, []).append(r.guardian_id)
        children_map.setdefault(r.guardian_id, []).append(r.child_id)

    artifacts = FAMILY_STORE.list_artifacts()
    tag_freq: Dict[str, int] = {}
    lines: List[str] = []

    for art in artifacts:
        pid = art.get("entity_id")
        person = people.get(pid)
        content_ref = art.get("content_ref")
        body_text = _read_content_ref(content_ref)
        if not body_text:
            meta_snip = _meta_snippet(art.get("meta", {}))
            body_text = f"Title: {art.get('title','')}\nTags: {', '.join(art.get('tags', []))}\n{meta_snip}".strip()
        text_hash = _hash_text(body_text)
        roles = person.roles if person else []
        grade_band = person.grade_band if person else None
        household_id = person.household_id if person else None
        guardians = guardians_map.get(pid, [])
        children = children_map.get(pid, [])
        tags = art.get("tags", []) or []
        for t in tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        derived = {
            "normalized_title": (art.get("title") or "").lower(),
            "tag_string": " ".join(tags),
            "token_count": _token_count(body_text),
            "text_hash": text_hash,
        }
        row = {
            "artifact_id": art["id"],
            "entity_id": pid,
            "kind": art.get("kind"),
            "title": art.get("title"),
            "text": body_text,
            "tags": tags,
            "meta": art.get("meta", {}),
            "grade_band": grade_band,
            "entity_roles": roles,
            "household_id": household_id,
            "guardians": guardians,
            "children": children,
            "derived_features": derived,
            "split": DEFAULT_SPLIT,
            "source_ref": content_ref,
        }
        lines.append(json.dumps(row, ensure_ascii=False))

    OUTPUT_JSONL.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    TAGS_SUMMARY.write_text(
        json.dumps({
            "total_artifacts": len(artifacts),
            "distinct_tags": len(tag_freq),
            "tag_freq": dict(sorted(tag_freq.items(), key=lambda x: (-x[1], x[0]))),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "artifacts": len(artifacts),
        "output": str(OUTPUT_JSONL),
        "tags_summary": str(TAGS_SUMMARY),
        "distinct_tags": len(tag_freq),
    }


if __name__ == "__main__":
    result = build_corpus()
    print(json.dumps(result))
