#!/usr/bin/env python3
"""Synchronize .env.example from current .env and code references.

Rules:
  - Never print or write real secret values (mask with placeholders).
  - Preserve existing ordering/comments in .env.example when possible (simple merge).
  - Add newly discovered variables (from .env or code) with categorized comments.
  - Keep variables not present in code/.env (manually added doc lines) untouched.

Classification heuristics (secret if any pattern matches key):
  - contains: KEY, TOKEN, SECRET, PASS, PASSWORD, PAT, SERVICE_KEY, ANON_KEY, JWT
  - endswith: _URL only if value appears to embed credentials (basic://user:pass@)

Usage:
  python scripts/sync_env_example.py [--write] [--env .env] [--example .env.example]
Without --write it performs a dry run diff summary.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

SECRET_PAT = re.compile(
    r"(KEY|TOKEN|SECRET|PASS|PASSWORD|PAT|SERVICE_KEY|ANON_KEY|JWT|WORKER|POOLER|PROJECT_REF)",
    re.IGNORECASE,
)


def is_secret(name: str, value: str) -> bool:
    if SECRET_PAT.search(name):
        return True
    if name.endswith("_URL") and re.search(r"://[^:@]+:[^@]+@", value):  # embedded creds
        return True
    return False


def parse_env_file(path: Path) -> Tuple[Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    raw_lines: List[str] = []
    if not path.exists():
        return mapping, raw_lines
    for line in path.read_text().splitlines():
        raw_lines.append(line)
        if not line or line.lstrip().startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            mapping[k.strip()] = v
    return mapping, raw_lines


def discover_code_env_vars(root: Path) -> List[str]:
    # Regex captures either os.getenv("NAME" or os.environ["NAME"] usage
    pattern = re.compile(r'os\.getenv\("([A-Z0-9_]+)"|os\.environ\["([A-Z0-9_]+)"\]')
    found: set[str] = set()
    for py in root.rglob("*.py"):
        try:
            txt = py.read_text(errors="ignore")
        except Exception:
            continue
        for m in pattern.finditer(txt):
            name = m.group(1) or m.group(2)
            if name:
                found.add(name)
    return sorted(found)


def mask_value(name: str, value: str) -> str:
    if not value:
        return ""
    if is_secret(name, value):
        return "__REDACTED__"
    # Provide a default placeholder if obviously path/host like
    if name.endswith("_HOST") and value:
        return value or "localhost"
    return value


SECTION_HEADER = "## Generated below (do not edit manually)"


def build_example(env_map: Dict[str, str], code_vars: List[str], original_lines: List[str]) -> List[str]:
    existing_keys = {k for k in env_map.keys()}
    code_set = set(code_vars)
    # Keys to include: union of env + code references
    all_keys = sorted(existing_keys | code_set)

    # Preserve original lines up until generated header (if present)
    out: List[str] = []
    before_header = True
    for line in original_lines:
        if line.strip() == SECTION_HEADER:
            before_header = False
            out.append(line)
            break
        out.append(line)
    if before_header:
        out.append(SECTION_HEADER)

    out.append("# Synchronized variable placeholders (values redacted if secret).")
    for key in all_keys:
        val = env_map.get(key, "")
        masked = mask_value(key, val)
        comment = "# secret" if masked == "__REDACTED__" else "# optional" if key not in env_map else "# provided"
        out.append(f"{key}={masked} {comment}".rstrip())
    out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=".env")
    ap.add_argument("--example", default=".env.example")
    ap.add_argument("--write", action="store_true")
    ap.add_argument(
        "--redacted-out",
        default=".env.redacted",
        help="Optional path to also write a fully redacted export (implies --write).",
    )
    args = ap.parse_args()

    env_path = Path(args.env)
    ex_path = Path(args.example)
    env_map, _ = parse_env_file(env_path)
    _, ex_lines = parse_env_file(ex_path)
    code_vars = discover_code_env_vars(Path("app"))
    new_lines = build_example(env_map, code_vars, ex_lines or ["## Environment Example"])

    write_mode = args.write or bool(args.redacted_out)
    if not write_mode:
        # Dry run: show diff stats only
        old = ex_path.read_text().splitlines() if ex_path.exists() else []
        added = len([l for l in new_lines if l not in old])
        removed = len([l for l in old if l not in new_lines])
        print(f"Dry run: would write {ex_path} (added {added} lines, removed {removed} lines). Use --write to apply.")
        return 0

    ex_path.write_text("\n".join(new_lines) + "\n")
    print(f"Updated {ex_path} with {len(new_lines)} lines (secrets redacted).")

    # Optionally produce a standalone redacted snapshot containing only key=__REDACTED__ or placeholder values.
    if args.redacted_out:
        redacted_lines: list[str] = ["# Auto-generated redacted environment snapshot", "# Do NOT use these values in production."]
        for k in sorted(env_map.keys()):
            v = env_map[k]
            redacted_lines.append(f"{k}={'__REDACTED__' if is_secret(k, v) else mask_value(k, v)}")
        Path(args.redacted_out).write_text("\n".join(redacted_lines) + "\n")
        print(f"Wrote redacted snapshot to {args.redacted_out} ({len(redacted_lines)} lines).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
