"""Wrapper launcher for the canonical Memory ↔ RAG Bridge.

This file exists because some tooling expects `scripts/memory_rag_bridge.py`.
The real implementation lives at `fine_tuning/tooling/rag/memory_rag_bridge.py`.

Usage examples:
  python scripts/memory_rag_bridge.py --once
  python scripts/memory_rag_bridge.py --search "vector databases" --top-k 5

Environment variables (forwarded):
  MEMORY_FILE_PATH, DATABASE_URL, EMBED_ENDPOINT, BATCH_SIZE, LOOP_INTERVAL

If the canonical path moves, update CANONICAL_PATH.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


CANONICAL_PATH = (
    Path(__file__).resolve().parent.parent
    / "fine_tuning"
    / "tooling"
    / "rag"
    / "memory_rag_bridge.py"
)


def main() -> None:
    if not CANONICAL_PATH.exists():  # graceful fallback
        sys.stderr.write(
            f"[memory_rag_bridge wrapper] Canonical script missing at {CANONICAL_PATH}\n"
        )
        sys.exit(1)

    # Delegate execution preserving CLI args
    runpy.run_path(str(CANONICAL_PATH), run_name="__main__")


if __name__ == "__main__":
    main()
