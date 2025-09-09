#!/usr/bin/env python3
"""Helpers to upsert and finalize entries in the ingestion_manifest table."""
from __future__ import annotations

import os
from typing import Iterable, Optional

import psycopg2  # type: ignore
from psycopg2.extras import Json  # type: ignore


DSN = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")


def create_or_update_manifest(
    batch_tag: str,
    files: Iterable[str],
    total_bytes: int,
    status: str = "queued",
    extra: Optional[dict] = None,
) -> None:
    if not DSN:
        return
    files_list = list(files)
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_manifest (batch_tag, status, files, total_files, total_bytes, extra)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (batch_tag)
            DO UPDATE SET status=EXCLUDED.status, files=EXCLUDED.files, total_files=EXCLUDED.total_files,
                          total_bytes=EXCLUDED.total_bytes, extra=EXCLUDED.extra, started_at=now();
            """,
            (batch_tag, status, Json(files_list), len(files_list), total_bytes, Json(extra or {})),
        )
        conn.commit()


def finish_manifest(batch_tag: str, status: str, error: Optional[str] = None) -> None:
    if not DSN:
        return
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingestion_manifest
            SET status=%s, finished_at=now(), error=%s
            WHERE batch_tag=%s;
            """,
            (status, error, batch_tag),
        )
        conn.commit()
