#!/usr/bin/env python3
"""
DB helper for colony swarm modules.

ENV:
  - DATABASE_URL or DB_DSN for Postgres connection (pgvector enabled recommended).

This module degrades gracefully when no DB is configured (methods no-op or return
mocked values). It is intended primarily as a storage adapter for the colony
dispatch and analytics modules.
"""
from __future__ import annotations

import os
import random
from typing import Dict, List, Tuple, Optional

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


class ColonyDB:
    def __init__(self, dsn: Optional[str] | None = None):
        self.dsn = dsn or os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
        self.conn = None
        if self.dsn and psycopg2 is not None:
            # psycopg2 connection type is dynamic; use Any to avoid strict typing issues
            self.conn = psycopg2.connect(self.dsn)  # type: ignore[no-untyped-call]

    @property
    def enabled(self) -> bool:
        return self.conn is not None

    def fetch_pheromones(self, colony_type: str) -> Dict[int, float]:
        if not self.enabled:
            return {}
        with self.conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(
                "SELECT shard_id, level FROM pheromones WHERE colony_type=%s",
                (colony_type,),
            )
            rows = cur.fetchall()
        return {int(sid): float(level) for sid, level in rows}

    def update_pheromone(self, colony_type: str, shard_id: int, delta: float) -> None:
        if not self.enabled:
            return
        with self.conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(
                """
                INSERT INTO pheromones (colony_type, shard_id, level)
                VALUES (%s, %s, %s)
                ON CONFLICT (colony_type, shard_id)
                DO UPDATE SET level = pheromones.level + EXCLUDED.level,
                              last_update = now()
                """,
                (colony_type, shard_id, delta),
            )
        self.conn.commit()  # type: ignore[union-attr]

    def run_query(self, vector, k: int = 10) -> List[Tuple[int, int, float]]:
        """
        Returns list of tuples: (id, shard_id, distance)
        Note: When DB is enabled, assumes pgvector and a table `embeddings` with columns (id, shard_id, vector).
        """
        if not self.enabled:
            return [(random.randint(1, 1_000_000), random.randint(0, 31), random.random()) for _ in range(k)]
        with self.conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(
                """
                SELECT id, shard_id, vector <-> %s AS dist
                FROM embeddings
                ORDER BY vector <-> %s
                LIMIT %s
                """,
                (vector, vector, k),
            )
            rows = cur.fetchall()
        # Ensure the return type is List[Tuple[int, int, float]]
        return [(int(r[0]), int(r[1]), float(r[2])) for r in rows]

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None
