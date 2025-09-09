#!/usr/bin/env python3
"""PII gate helper: a simple lock row living in the PII database.

Table: pii_ingestion_gate(batch_tag text primary key, locked boolean not null default true,
       created_at timestamptz default now(), opened_at timestamptz)

Env:
  PII_DATABASE_URL  (required)

CLI:
  ensure --batch-tag TAG
  open   --batch-tag TAG
  is-open --batch-tag TAG
  wait  --batch-tag TAG [--timeout 600] [--interval 3]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import psycopg2  # type: ignore


PII_DSN = os.getenv("PII_DATABASE_URL")


def require_dsn() -> str:
    if not PII_DSN:
        print("PII_DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    return PII_DSN  # type: ignore[return-value]


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pii_ingestion_gate (
                batch_tag text PRIMARY KEY,
                locked boolean NOT NULL DEFAULT true,
                created_at timestamptz DEFAULT now(),
                opened_at timestamptz
            );
            """
        )
        conn.commit()


def cmd_ensure(tag: str) -> int:
    dsn = require_dsn()
    with psycopg2.connect(dsn) as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pii_ingestion_gate (batch_tag, locked)
                VALUES (%s, true)
                ON CONFLICT (batch_tag) DO NOTHING;
                """,
                (tag,),
            )
            conn.commit()
    return 0


def cmd_open(tag: str) -> int:
    dsn = require_dsn()
    with psycopg2.connect(dsn) as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pii_ingestion_gate
                SET locked=false, opened_at=now()
                WHERE batch_tag=%s;
                """,
                (tag,),
            )
            if cur.rowcount == 0:
                # Create then open
                cur.execute(
                    """
                    INSERT INTO pii_ingestion_gate (batch_tag, locked, opened_at)
                    VALUES (%s, false, now())
                    ON CONFLICT (batch_tag) DO UPDATE SET locked=false, opened_at=excluded.opened_at;
                    """,
                    (tag,),
                )
            conn.commit()
    return 0


def is_open(tag: str) -> bool:
    dsn = require_dsn()
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT NOT locked FROM pii_ingestion_gate WHERE batch_tag=%s;", (tag,))
        row = cur.fetchone()
        return bool(row and row[0])


def cmd_is_open(tag: str) -> int:
    print("true" if is_open(tag) else "false")
    return 0


def cmd_wait(tag: str, timeout: int, interval: int) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_open(tag):
            return 0
        time.sleep(interval)
    print("timeout", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="PII gate management")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_ensure = sub.add_parser("ensure")
    ap_ensure.add_argument("--batch-tag", required=True)

    ap_open = sub.add_parser("open")
    ap_open.add_argument("--batch-tag", required=True)

    ap_is = sub.add_parser("is-open")
    ap_is.add_argument("--batch-tag", required=True)

    ap_wait = sub.add_parser("wait")
    ap_wait.add_argument("--batch-tag", required=True)
    ap_wait.add_argument("--timeout", type=int, default=600)
    ap_wait.add_argument("--interval", type=int, default=3)

    args = ap.parse_args()
    if args.cmd == "ensure":
        return cmd_ensure(args.batch_tag)
    if args.cmd == "open":
        return cmd_open(args.batch_tag)
    if args.cmd == "is-open":
        return cmd_is_open(args.batch_tag)
    if args.cmd == "wait":
        return cmd_wait(args.batch_tag, args.timeout, args.interval)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
