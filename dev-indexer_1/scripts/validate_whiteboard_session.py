#!/usr/bin/env python3
"""Validate a whiteboard session JSON file against the schema.

Usage:
  python scripts/validate_whiteboard_session.py path/to/session.json [--schema docs/whiteboard_session.schema.json]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    print("Missing dependency jsonschema. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(2)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(session_path: Path, schema_path: Path) -> None:
    schema = load_json(schema_path)
    session = load_json(session_path)
    jsonschema.validate(instance=session, schema=schema)
    # lightweight semantic checks
    if session.get("version") != "v1":
        raise ValueError(f"Unsupported session version: {session.get('version')}")
    events = session.get("events", [])
    if not events:
        raise ValueError("Session has no events")
    last_t = 0
    for ev in events:
        t = ev.get("t")
        if not isinstance(t, int) or t < 0:
            raise ValueError(f"Invalid event timestamp: {t}")
        if t < last_t:
            raise ValueError(f"Event timestamps not monotonic: {t} < {last_t}")
        last_t = t
    print(
        json.dumps(
            {
                "status": "ok",
                "session": session.get("session_id"),
                "event_count": len(events),
                "audio_sha256": session.get("audio", {}).get("sha256"),
                "file_sha256": sha256_file(session_path),
            },
            indent=2,
        )
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session_json", type=Path)
    # Default path adjusted to docs/whiteboard_session.schema.json since docs/schemas/ does not exist
    p.add_argument("--schema", type=Path, default=Path("docs/whiteboard_session.schema.json"))
    args = p.parse_args()
    try:
        validate(args.session_json, args.schema)
    except jsonschema.ValidationError as ve:
        print(f"Schema validation error: {ve.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # pragma: no cover
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
