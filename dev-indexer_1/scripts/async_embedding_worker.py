#!/usr/bin/env python3
"""Stub retained for backward compatibility.

Legacy script archived at:
	archive/async_embedding_worker_legacy.py

Forward worker:
	app/inference/gating.py (psycopg v3)

This stub intentionally exits to prevent accidental use.
"""
from __future__ import annotations
import sys

def main() -> int:  # pragma: no cover - trivial stub
		print(
				"[deprecated] scripts/async_embedding_worker.py moved to archive/async_embedding_worker_legacy.py; "
				"use app/inference/gating.py instead",
				file=sys.stderr,
		)
		return 1

if __name__ == "__main__":  # pragma: no cover
		raise SystemExit(main())
