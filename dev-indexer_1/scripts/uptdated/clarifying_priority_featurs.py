"""Clarifying Priority Feature Extraction (V0)

Generates a structured feature dictionary for a chunk to feed a tiny
prioritization model (GBDT / linear / ranker). Focuses on cheap textual
signals first; additional retrieval & interaction features can be merged later.

Design:
  extract_features(text, context=None) -> (features: dict, meta: dict)

Feature Groups Implemented (cheap set):
  length:
    - char_len
    - word_len
    - avg_sentence_len
    - sentence_count
    - sentence_len_stdev (naive)
  lexical:
    - pronoun_early_count (this/that/it/these/those first 160 chars)
    - acronym_count (ALLCAPS 2-6)
    - capitalized_entity_count (Capitalized >=4 letters)
  - numeric_unit_count (\\d+(ms|gb|mb|%|s|sec|secs|minutes|hrs|x))
    - todo_marker (0/1)
    - placeholder_marker (0/1 for <...> or {...})
  ratios:
    - capitals_per_100_words
    - acronyms_per_100_words
  ambiguity:
    - unresolved_pronoun_ratio (pronoun_early_count / word_len_clamped)

Planned Additions:
  - glossary_gap_rate
  - embedding_novelty
  - churn / staleness
  - retrieval_miss_rate
  - coref_chain_count

All numeric features are floats (even if integral) to simplify model pipelines.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple
import math, re, statistics

PRONOUN_PATTERN = re.compile(r"\b(this|that|these|those|it)\b", re.IGNORECASE)
ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,6}\b")
CAP_ENTITY_PATTERN = re.compile(r"\b[A-Z][a-z]{3,}\b")
NUM_UNIT_PATTERN = re.compile(r"\b\d+(?:ms|gb|mb|%|s|sec|secs|minutes|hrs|x)\b", re.IGNORECASE)
PLACEHOLDER_PATTERN = re.compile(r"[<{][^\n]{1,40}[>}]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str):
    # Simple split; avoids heavy NLP dependency
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def extract_features(text: str, context: Dict[str, Any] | None = None) -> Tuple[Dict[str, float], Dict[str, Any]]:
    context = context or {}
    features: Dict[str, float] = {}

    char_len = len(text)
    words = re.findall(r"\w+", text)
    word_len = len(words)
    features["char_len"] = float(char_len)
    features["word_len"] = float(word_len)

    # Sentences
    sents = _sentences(text)
    sent_lengths = [len(re.findall(r"\w+", s)) for s in sents]
    if sent_lengths:
        avg_sent = sum(sent_lengths)/len(sent_lengths)
        stdev_sent = statistics.pstdev(sent_lengths) if len(sent_lengths) > 1 else 0.0
    else:
        avg_sent = 0.0
        stdev_sent = 0.0
    features["sentence_count"] = float(len(sents))
    features["avg_sentence_len"] = float(avg_sent)
    features["sentence_len_stdev"] = float(stdev_sent)

    early_window = text[:160]
    pronouns_early = PRONOUN_PATTERN.findall(early_window)
    features["pronoun_early_count"] = float(len(pronouns_early))

    acronyms = ACRONYM_PATTERN.findall(text)
    features["acronym_count"] = float(len(acronyms))

    cap_entities = CAP_ENTITY_PATTERN.findall(text)
    features["capitalized_entity_count"] = float(len(cap_entities))

    num_units = NUM_UNIT_PATTERN.findall(text)
    features["numeric_unit_count"] = float(len(num_units))

    features["todo_marker"] = 1.0 if any(k in text.lower() for k in ("todo","fixme","tbd")) else 0.0
    features["placeholder_marker"] = 1.0 if PLACEHOLDER_PATTERN.search(text) else 0.0

    # Ratios (avoid div by 0)
    denom = max(1, word_len)
    features["capitals_per_100_words"] = (len(cap_entities)/denom) * 100.0
    features["acronyms_per_100_words"] = (len(acronyms)/denom) * 100.0
    features["unresolved_pronoun_ratio"] = (len(pronouns_early)/denom)

    # Light transforms
    features["log_char_len"] = math.log(max(1, char_len))
    features["log_word_len"] = math.log(max(1, word_len))

    meta = {"version": 0, "context_keys": list(context.keys())}
    return features, meta


__all__ = ["extract_features"]
