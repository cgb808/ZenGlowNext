"""Generate synthetic conversational fine-tune samples from family context.

Output: JSONL where each line is an object:
  {
    "messages": [ {"role": "system", "content": "..."}, {"role": "user", ...}, ...],
    "meta": { "scenario": "artifact_retrieval" }
  }

Patterns implemented:
1. artifact_retrieval - user asks for info about an artifact; assistant cites tags.
2. health_metric - user asks for latest health metric; assistant answers.
3. guardianship_policy - user requests sensitive detail; assistant refuses and offers summary.
4. follow_up - multi-turn follow-up referencing prior response (coreference).
5. multi_artifact_compare - user compares two artifacts; assistant summarizes differences.

Future extensions: timeline_event tutoring sessions, cross-sibling comparisons w/ guardrails, multi-model orchestration traces.
"""
from __future__ import annotations
import json, sys, pathlib
from typing import List, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.family.context import ensure_seed, FAMILY_STORE  # noqa: E402


def sys_prompt() -> str:
    return (
        "You are a family tutoring & data assistant. Be privacy aware. "
        "For minors: never reveal exact birthdate or location. Provide concise, factual answers."
    )


def artifact_retrieval_examples(max_per_entity: int = 2):
    for art in FAMILY_STORE.list_artifacts(limit=1000):
        user_q = f"Can you summarize the {art['kind']} titled '{art['title']}' for {art['entity_id']}?"
        assistant_a = (
            f"The {art['kind']} '{art['title']}' for {art['entity_id']} has tags: "
            + ", ".join(art.get('tags', []) or ["none"]) + "."
        )
        yield {
            "messages": [
                {"role": "system", "content": sys_prompt()},
                {"role": "user", "content": user_q},
                {"role": "assistant", "content": assistant_a},
            ],
            "meta": {"scenario": "artifact_retrieval", "artifact_id": art["id"]},
        }


def health_metric_examples():
    # Access protected internal structure cautiously; treat as ephemeral
    for pid, buckets in getattr(FAMILY_STORE, "_buckets", {}).items():  # type: ignore[attr-defined]
        metrics = buckets.get("health", [])
        if not metrics:
            continue
        latest = metrics[-1]
        q = f"What is the latest {latest['metric']} for {pid}?"
        a = f"Latest {latest['metric']} for {pid} is {latest['value']}{latest.get('unit','')} recorded most recently."
        yield {
            "messages": [
                {"role": "system", "content": sys_prompt()},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ],
            "meta": {"scenario": "health_metric", "entity_id": pid},
        }


def guardianship_policy_examples():
    # Choose a child (grade_band not adult) and ask for sensitive info
    for p in FAMILY_STORE.list_people():
        if p.grade_band == "adult":
            continue
        q = f"Please give me {p.name}'s full birthdate and home address."
        a = (
            f"I can't share {p.name}'s exact birthdate or address. "
            f"They are in grade band {p.grade_band} and I can provide general academic summaries if needed."
        )
        yield {
            "messages": [
                {"role": "system", "content": sys_prompt()},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ],
            "meta": {"scenario": "guardianship_policy", "entity_id": p.id},
        }
        break  # only one needed for now


def follow_up_examples():
    # Build on an artifact question with a follow-up
    arts = FAMILY_STORE.list_artifacts(limit=10)
    if not arts:
        return
    art = arts[0]
    msgs = [
        {"role": "system", "content": sys_prompt()},
        {"role": "user", "content": f"Tell me about '{art['title']}'."},
        {"role": "assistant", "content": f"It's a {art['kind']} tagged with: {', '.join(art.get('tags', []) or ['none'])}."},
        {"role": "user", "content": "Does it indicate progress?"},
        {"role": "assistant", "content": "Yes, tags suggest achievement or focus areas; you can compare with prior artifacts for trend."},
    ]
    yield {"messages": msgs, "meta": {"scenario": "follow_up", "artifact_id": art["id"]}}


def multi_artifact_compare_examples():
    arts = FAMILY_STORE.list_artifacts(limit=10)
    if len(arts) < 2:
        return
    a1, a2 = arts[0], arts[1]
    msgs = [
        {"role": "system", "content": sys_prompt()},
        {"role": "user", "content": f"Compare '{a1['title']}' with '{a2['title']}'."},
        {"role": "assistant", "content": (
            f"'{a1['title']}' tags: {', '.join(a1.get('tags', []) or ['none'])}; "
            f"'{a2['title']}' tags: {', '.join(a2.get('tags', []) or ['none'])}."
        )},
        {"role": "user", "content": "Which seems more academic?"},
        {"role": "assistant", "content": "The assessment document is more academic; the photo evidences project-based learning."},
    ]
    yield {"messages": msgs, "meta": {"scenario": "multi_artifact_compare", "a1": a1["id"], "a2": a2["id"]}}


GENERATORS = [
    artifact_retrieval_examples,
    health_metric_examples,
    guardianship_policy_examples,
    follow_up_examples,
    multi_artifact_compare_examples,
]


def main() -> int:
    ensure_seed()
    count = 0
    for gen in GENERATORS:
        for sample in gen():
            json.dump(sample, sys.stdout)
            sys.stdout.write("\n")
            count += 1
    return 0 if count else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
