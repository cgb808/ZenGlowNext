#!/usr/bin/env python3
import argparse
import os
import sys
import uuid
from typing import Any, Dict

import yaml
import psycopg2
from psycopg2.extras import Json


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def connect(dsn: str):
    return psycopg2.connect(dsn)


def upsert_family_core(conn, data: Dict[str, Any]):
    hh = data.get("household_id")
    people = data.get("people", [])
    rels = data.get("relationships", [])
    artifacts = data.get("artifacts", [])
    health = data.get("health_metrics", [])

    with conn, conn.cursor() as cur:
        for p in people:
            cur.execute(
                """
                INSERT INTO family_people(id, name, age, grade_band, last_name, birthdate, household_id, meta)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  name=EXCLUDED.name,
                  age=EXCLUDED.age,
                  grade_band=EXCLUDED.grade_band,
                  last_name=EXCLUDED.last_name,
                  birthdate=EXCLUDED.birthdate,
                  household_id=EXCLUDED.household_id,
                  meta=EXCLUDED.meta,
                  updated_ts=now()
                """,
                (
                    p["id"],
                    p.get("name"),
                    int(p.get("age") or 0),
                    p.get("grade_band", "unknown"),
                    p.get("last_name"),
                    p.get("birthdate"),
                    hh,
                    Json(p.get("meta") or {}),
                ),
            )

        for r in rels:
            cur.execute(
                """
                INSERT INTO family_relationships(guardian_id, child_id, kind, legal)
                VALUES (%s,%s,%s, TRUE)
                ON CONFLICT (guardian_id, child_id, kind) DO NOTHING
                """,
                (r["guardian_id"], r["child_id"], r.get("kind", "guardian")),
            )

        for a in artifacts:
            cur.execute(
                """
                INSERT INTO family_artifacts(id, entity_id, kind, title, tags, content_ref, meta)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    a["id"],
                    a["entity_id"],
                    a.get("kind", "note"),
                    a.get("title", "Untitled"),
                    a.get("tags", []),
                    a.get("content_ref"),
                    Json(a.get("meta") or {}),
                ),
            )

        for h in health:
            cur.execute(
                """
                INSERT INTO family_health_metrics(entity_id, metric, value_text, value_num, unit, ts)
                VALUES (%s,%s,%s,%s,%s, now())
                """,
                (
                    h["entity_id"],
                    h.get("metric"),
                    h.get("value_text"),
                    h.get("value_num"),
                    h.get("unit"),
                ),
            )


def upsert_pii(conn, data: Dict[str, Any], map_tokens: bool = True):
    people = data.get("people", [])
    # Naive mapping: one identity per person id; copy names/birthdate if present
    with conn, conn.cursor() as cur:
        for p in people:
            ident = uuid.uuid5(uuid.NAMESPACE_URL, f"family:{p['id']}")
            cur.execute(
                """
                INSERT INTO pii_identity_profiles(
                  id, subject_type, subject_ref, legal_name, preferred_name, birthdate, email, phone, address_line1, meta
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  preferred_name=EXCLUDED.preferred_name,
                  birthdate=EXCLUDED.birthdate,
                  updated_ts=now()
                """,
                (
                    str(ident),
                    "person",
                    p["id"],
                    f"{p.get('name','')} {p.get('last_name','')}".strip() or None,
                    p.get("name"),
                    p.get("birthdate"),
                    None,
                    None,
                    None,
                    Json(p.get("meta") or {}),
                ),
            )
            if map_tokens:
                # Ensure a token exists (if none valid, mint one via SQL helper)
                cur.execute(
                    "SELECT token FROM pii_token_map WHERE identity_id=%s AND (valid_until IS NULL OR valid_until > now()) LIMIT 1",
                    (str(ident),),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute("SELECT mint_user_token(%s, 'family', NULL)", (str(ident),))


def main():
    ap = argparse.ArgumentParser(description="Seed family data into core and PII DBs")
    ap.add_argument("--yaml", required=True, help="YAML seed file path")
    ap.add_argument(
        "--core-dsn",
        default=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag_db"),
        help="Core DB DSN",
    )
    ap.add_argument(
        "--pii-dsn",
        default=os.getenv("PII_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/rag_pii"),
        help="PII DB DSN",
    )
    ap.add_argument("--no-token-map", action="store_true", help="Skip creating token map entries")
    args = ap.parse_args()

    data = load_yaml(args.yaml)

    try:
        with connect(args.core_dsn) as core_conn:
            upsert_family_core(core_conn, data)
        with connect(args.pii_dsn) as pii_conn:
            upsert_pii(pii_conn, data, map_tokens=(not args.no_token_map))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Seed complete.")


if __name__ == "__main__":
    main()
