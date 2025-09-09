#!/usr/bin/env python3
"""
Dev JWT helper.

Mint and decode HS256 JWTs using a shared secret from env or CLI.

Examples:
  Mint (1h):
    python scripts/dev_jwt.py mint --sub alice --aud dev --exp 3600

  Decode:
    python scripts/dev_jwt.py decode --token <JWT>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

try:
    import jwt  # PyJWT
except Exception as exc:  # pragma: no cover
    print("PyJWT not installed. Add 'PyJWT' to requirements and install.", file=sys.stderr)
    raise


def _get_secret(cli_secret: str | None) -> str:
    secret = cli_secret or os.getenv("JWT_SECRET")
    if not secret:
        print("JWT_SECRET not set. Provide via --secret or .env", file=sys.stderr)
        sys.exit(2)
    if len(secret) < 16:
        print("Warning: JWT secret is very short; increase length for safety.", file=sys.stderr)
    return secret


def cmd_mint(args: argparse.Namespace) -> None:
    secret = _get_secret(args.secret)
    now = int(time.time())
    claims: Dict[str, Any] = {
        "iat": now,
        "exp": now + int(args.exp),
    }
    if args.sub:
        claims["sub"] = args.sub
    if args.aud:
        claims["aud"] = args.aud
    if args.scope:
        claims["scope"] = args.scope
    # Merge arbitrary JSON claims
    if args.claims:
        try:
            extra = json.loads(args.claims)
            if not isinstance(extra, dict):
                raise ValueError("claims must be a JSON object")
            claims.update(extra)
        except Exception as e:
            print(f"Invalid --claims JSON: {e}", file=sys.stderr)
            sys.exit(2)

    token = jwt.encode(claims, secret, algorithm="HS256")
    # PyJWT returns str on new versions
    print(token)


def cmd_decode(args: argparse.Namespace) -> None:
    secret = _get_secret(args.secret) if args.verify else None
    options = {"verify_signature": bool(args.verify)}
    try:
        if secret:
            data = jwt.decode(args.token, secret, algorithms=["HS256"])
        else:
            # decode without verification for quick inspection
            data = jwt.api_jwt.decode_complete(args.token, options=options)
            data = data.get("payload", {})
        print(json.dumps(data, indent=2, sort_keys=True))
    except Exception as e:
        print(f"Decode error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(description="Dev JWT mint/decode helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_mint = sub.add_parser("mint", help="Mint a dev JWT")
    p_mint.add_argument("--sub", help="subject", default=None)
    p_mint.add_argument("--aud", help="audience", default=None)
    p_mint.add_argument("--scope", help="scope string", default=None)
    p_mint.add_argument("--exp", help="expiry seconds (default 3600)", default=3600)
    p_mint.add_argument("--claims", help="extra claims as JSON object", default=None)
    p_mint.add_argument("--secret", help="override JWT secret", default=None)
    p_mint.set_defaults(func=cmd_mint)

    p_dec = sub.add_parser("decode", help="Decode a JWT (optionally verify)")
    p_dec.add_argument("--token", required=True)
    p_dec.add_argument("--verify", action="store_true", help="verify signature using secret")
    p_dec.add_argument("--secret", help="JWT secret for verification", default=None)
    p_dec.set_defaults(func=cmd_decode)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
