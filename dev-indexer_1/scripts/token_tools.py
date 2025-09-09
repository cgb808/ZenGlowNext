#!/usr/bin/env python3
"""
Token tools for PII vault

CLI to mint, resolve, and rotate pseudonymous user tokens stored in pii_token_map.
Uses PII_DATABASE_URL from environment (e.g., postgresql://user:pass@host:5432/rag_pii).

Examples:
  Mint:    token_tools.py mint --identity <uuid> [--purpose voice_auth] [--ttl 30]
  Resolve: token_tools.py resolve --token <token>
  Rotate:  token_tools.py rotate --token <token> [--ttl 30]
"""
import argparse
import os
import sys
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    url = os.getenv("PII_DATABASE_URL")
    if not url:
        print("PII_DATABASE_URL env var is required", file=sys.stderr)
        sys.exit(2)
    return psycopg2.connect(url)


def mint(identity: str, purpose: str, ttl: Optional[int]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mint_user_token(%s::uuid, %s::text, %s::int)",
                (identity, purpose, ttl),
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                print("failed to mint token", file=sys.stderr)
                sys.exit(1)
            print(row[0])


def resolve(token: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT resolve_identity(%s)", (token,))
            row = cur.fetchone()
            ident = row[0] if row else None
            if ident is None:
                print("", end="")  # empty output for not found/expired
            else:
                print(ident)


def rotate(token: str, ttl: Optional[int]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT rotate_user_token(%s, %s::int)", (token, ttl))
            row = cur.fetchone()
            if not row or row[0] is None:
                print("failed to rotate token", file=sys.stderr)
                sys.exit(1)
            print(row[0])


def main():
    ap = argparse.ArgumentParser(prog="token_tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_mint = sub.add_parser("mint", help="mint a token for identity UUID")
    ap_mint.add_argument("--identity", required=True, help="identity UUID")
    ap_mint.add_argument("--purpose", default="data_link")
    ap_mint.add_argument("--ttl", type=int, default=None, help="TTL in days")

    ap_res = sub.add_parser("resolve", help="resolve identity UUID from token")
    ap_res.add_argument("--token", required=True)

    ap_rot = sub.add_parser("rotate", help="rotate token and return new token")
    ap_rot.add_argument("--token", required=True)
    ap_rot.add_argument("--ttl", type=int, default=None)

    args = ap.parse_args()

    if args.cmd == "mint":
        mint(args.identity, args.purpose, args.ttl)
    elif args.cmd == "resolve":
        resolve(args.token)
    elif args.cmd == "rotate":
        rotate(args.token, args.ttl)
    else:
        ap.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
