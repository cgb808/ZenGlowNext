"""Sync in-memory seed data to Postgres persistence layer.

Prereqs:
  - Set FAMILY_PG_DSN env var (e.g. postgresql://user:pass@localhost:5432/db)
  - psycopg2-binary installed (in requirements).

Usage:
  python scripts/family_persist_sync.py --apply
"""
from __future__ import annotations
import os, argparse
from app.family.context import ensure_seed, FAMILY_STORE, Relationship
from app.family.pg_repo import PgFamilyRepo, ensure_schema

DEFAULT_SCHEMA = 'sql/family_schema.sql'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--schema', default=DEFAULT_SCHEMA)
    ap.add_argument('--apply', action='store_true', help='Execute sync (required flag to avoid accidents)')
    args = ap.parse_args()

    dsn = os.getenv('FAMILY_PG_DSN')
    if not dsn:
        print('FAMILY_PG_DSN not set; aborting', flush=True)
        return 1
    if not args.apply:
        print('Dry run (add --apply to execute).', flush=True)
        return 0

    ensure_seed()
    ensure_schema(dsn, args.schema)
    repo = PgFamilyRepo(dsn)

    # People
    for p in FAMILY_STORE.list_people():
        repo.upsert_person({
            'id': p.id,
            'name': p.name,
            'age': p.age,
            'grade_band': p.grade_band,
            'last_name': p.last_name,
            'birthdate': p.birthdate,
            'household_id': p.household_id,
            'meta': p.meta,
        })
    # Relationships
    for rel in getattr(FAMILY_STORE, '_relationships', []):
        if isinstance(rel, Relationship):
            repo.add_guardian(rel.guardian_id, rel.child_id, rel.legal)
    # Artifacts
    for art in FAMILY_STORE.list_artifacts(limit=1000):
        repo.add_artifact(art)
    # Health metrics (bucket items)
    for pid, buckets in getattr(FAMILY_STORE, '_buckets', {}).items():  # type: ignore
        for item in buckets.get('health', []):
            repo.add_health_metric(pid, item.get('metric','unknown'), item.get('value'), item.get('unit'))

    print('Sync complete.', flush=True)
    return 0

if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
