#!/usr/bin/env python3
"""
YAML Sanitizer: mass-correct YAML files in-place.
- Convert hard tabs to spaces (2 spaces)
- Fix common Compose/GitHub Actions issues (bad restart syntax, mis-indented env)
- Optionally reformat with ruamel.yaml round-trip for stable indentation

Usage:
  python scripts/yaml_sanitizer.py [paths...]
    If no paths provided, defaults to:
      - .github/workflows/*.yml
      - docker-compose*.yml
      - .vscode/docker-compose.yml
      - .yamllint.yml

Notes:
- Safe: creates a .bak alongside each file before writing.
- Does not introduce speculative keys; only formatting/safe value normalizations.
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys
from typing import Iterable, List

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
except Exception:  # pragma: no cover
    YAML = None  # type: ignore
    DoubleQuotedScalarString = None  # type: ignore

TAB_RE = re.compile(r"\t+")
BAD_RESTART_RE = re.compile(r"^\s*restart:\s*on-failure\s*:?\s*0\s*$", re.IGNORECASE)
UNQUOTED_COLON_IN_VALUE_RE = re.compile(
    r"^(\s*[^:#\n]+:\s*)([^'\"\[{][^#\n]*:[^#\n]*)$"
)

DEFAULT_GLOBS = [
    ".github/workflows/*.yml",
    "docker-compose*.yml",
    ".vscode/docker-compose.yml",
    ".yamllint.yml",
]


def find_files(paths: List[str]) -> List[str]:
    files: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for ext in (".yml", ".yaml"):
                files.extend(glob.glob(os.path.join(p, f"**/*{ext}"), recursive=True))
        else:
            matches = glob.glob(p)
            files.extend([m for m in matches if os.path.isfile(m)])
    # de-dup while preserving order
    seen = set()
    uniq: List[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def sanitize_text(content: str) -> str:
    # 1) Replace tabs with 2 spaces (not inside code fences since it's YAML files only)
    content = TAB_RE.sub("  ", content)

    lines = content.splitlines()
    fixed: List[str] = []
    for line in lines:
        # 2) Fix bad restart syntax like: restart: on-failure:0 -> restart: on-failure:0 (quoted)
        if BAD_RESTART_RE.match(line):
            # Normalize by quoting the value fully or switch to unless-stopped (dev-friendly)
            line = re.sub(r"on-failure\s*:?\s*0", '"on-failure:0"', line)

        # 3) Quote values containing colons that could be parsed as nested mappings (common in JWTs)
        m = UNQUOTED_COLON_IN_VALUE_RE.match(line)
        if m:
            prefix, val = m.groups()
            # Don't re-quote URLs (contain ://) if already quoted; otherwise quote
            if "://" not in val:
                line = f"{prefix}'{val.strip()}'"

        fixed.append(line)

    return "\n".join(fixed) + ("\n" if content.endswith("\n") else "\n")


def ruamel_roundtrip(path: str, text: str) -> str:
    if YAML is None:
        return text
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 120
    yaml.indent(mapping=2, sequence=2, offset=0)
    data = yaml.load(io.StringIO(text))
    buf = io.StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()


def process_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        print(f"skip {path}: read error: {e}")
        return False

    updated = sanitize_text(original)

    # Round-trip formatting only for compose/workflow yamls to standardize indentation
    if (
        path.endswith("docker-compose.yml")
        or "/workflows/" in path
        or path.endswith(".yamllint.yml")
        or path.endswith("docker-stack.yml")
        or path.endswith("docker-compose.dev-core.yml")
        or path.endswith(".vscode/docker-compose.yml")
    ):
        try:
            updated = ruamel_roundtrip(path, updated)
        except Exception as e:
            # Fall back silently; we already did safe textual fixes
            print(f"warn {path}: ruamel round-trip failed: {e}")

    if updated == original:
        return False

    # Backup
    try:
        with open(path + ".bak", "w", encoding="utf-8") as b:
            b.write(original)
    except Exception as e:
        print(f"warn {path}: could not write backup: {e}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"fixed {path}")
    return True


def main(argv: Iterable[str]) -> int:
    ap = argparse.ArgumentParser(description="Mass-correct YAML files in-place")
    ap.add_argument(
        "paths",
        nargs="*",
        help="Files or globs; defaults target common YAML files if omitted",
    )
    args = ap.parse_args(list(argv))

    targets = find_files(args.paths if args.paths else DEFAULT_GLOBS)
    if not targets:
        print("no YAML files matched")
        return 0

    changed = 0
    for p in targets:
        if process_file(p):
            changed += 1

    print(f"done. changed={changed}, scanned={len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
