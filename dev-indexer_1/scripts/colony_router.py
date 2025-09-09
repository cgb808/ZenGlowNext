#!/usr/bin/env python3
"""
Colony router: star/ring/explorer dispatch with optional DB integration.

- Uses psycopg2 + pgvector schema when DATABASE_URL is set.
- Falls back to a dry-run mode with in-memory pheromones/results otherwise.

CLI:
  python scripts/colony_router.py --k 10 --shards 32 --dry-run
  DATABASE_URL=postgres://... python scripts/colony_router.py --k 10 --shards 32
"""
import os
import time
import random
import argparse
from typing import Dict, List, Tuple

import numpy as np

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


class DB:
    def __init__(self, dsn: str | None):
        self.dsn = dsn
        self.conn = None
        if dsn and psycopg2 is not None:
            self.conn = psycopg2.connect(dsn)

    def fetch_pheromones(self, colony_type: str) -> Dict[int, float]:
        if not self.conn:
            return {}
        with self.conn.cursor() as cur:
            cur.execute("SELECT shard_id, level FROM pheromones WHERE colony_type=%s", (colony_type,))
            rows = cur.fetchall()
        return {sid: float(level) for sid, level in rows}

    def update_pheromone(self, colony_type: str, shard_id: int, delta: float) -> None:
        if not self.conn:
            return
        with self.conn.cursor() as cur:
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
        self.conn.commit()

    def run_query(self, vector: np.ndarray, k: int = 10) -> List[Tuple[int, int, float]]:
        if not self.conn:
            # Return mock (id, shard_id, distance)
            return [(random.randint(1, 1000), random.randint(0, 31), random.random()) for _ in range(k)]
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, shard_id, vector <-> %s AS dist
                FROM embeddings
                ORDER BY vector <-> %s
                LIMIT %s
                """,
                (vector, vector, k),
            )
            return cur.fetchall()


class ColonyRouter:
    def __init__(self, db: DB, shards: int = 32):
        self.db = db
        self.shards = list(range(shards))
        self._ring_ptr = 0

    def star_dispatch(self, qvec: np.ndarray, num_ants: int) -> List[Tuple[int, int, float]]:
        pher = self.db.fetch_pheromones("star")
        ranked = sorted(self.shards, key=lambda s: pher.get(s, 0.0), reverse=True)
        chosen = ranked[: max(1, num_ants)]
        results: List[Tuple[int, int, float]] = []
        for shard in chosen:
            res = self.db.run_query(qvec)
            results.extend(res)
            for _, sid, dist in res:
                self.db.update_pheromone("star", sid, 1.0 / (1.0 + float(dist)))
        return results

    def ring_dispatch(self, qvec: np.ndarray, num_ants: int) -> List[Tuple[int, int, float]]:
        results: List[Tuple[int, int, float]] = []
        for _ in range(max(1, num_ants)):
            shard = self.shards[self._ring_ptr % len(self.shards)]
            self._ring_ptr += 1
            res = self.db.run_query(qvec)
            results.extend(res)
            for _, sid, dist in res:
                self.db.update_pheromone("ring", sid, 1.0 / (1.0 + float(dist)))
        return results

    def explorer_dispatch(self, qvec: np.ndarray, num_ants: int) -> List[Tuple[int, int, float]]:
        pher = self.db.fetch_pheromones("explorer")
        ranked = sorted(self.shards, key=lambda s: pher.get(s, 0.0))
        chosen = ranked[: max(1, num_ants)]
        results: List[Tuple[int, int, float]] = []
        for shard in chosen:
            res = self.db.run_query(qvec)
            results.extend(res)
            for _, sid, dist in res:
                novelty_bonus = random.uniform(0.5, 1.5)
                self.db.update_pheromone("explorer", sid, novelty_bonus / (1.0 + float(dist)))
        return results

    def handle_query(self, qvec: np.ndarray, star_ratio=0.4, ring_ratio=0.4, explorer_ratio=0.2, k: int = 10):
        n = len(self.shards)
        star_results = self.star_dispatch(qvec, num_ants=max(1, int(n * star_ratio)))
        ring_results = self.ring_dispatch(qvec, num_ants=max(1, int(n * ring_ratio)))
        explorer_results = self.explorer_dispatch(qvec, num_ants=max(1, int(n * explorer_ratio)))
        all_results = star_results + ring_results + explorer_results
        ranked = sorted(all_results, key=lambda r: r[2])[:k]  # sort by distance
        return ranked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--shards", type=int, default=32)
    ap.add_argument("--dry-run", action="store_true", help="Use mock in-memory instead of DB")
    args = ap.parse_args()

    dsn = None if args.dry_run else os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
    db = DB(dsn)
    router = ColonyRouter(db, shards=args.shards)

    # random unit vector for demo
    qvec = np.random.rand(768).astype(np.float32)
    qvec = qvec / (np.linalg.norm(qvec) + 1e-8)

    t0 = time.time()
    ranked = router.handle_query(qvec, k=args.k)
    dt = (time.time() - t0) * 1000.0
    print(f"ranked top-{args.k} (len={len(ranked)}), latency_ms={dt:.2f}")
    for rid, sid, dist in ranked[:5]:
        print(f"  id={rid} shard={sid} dist={dist:.4f}")


if __name__ == "__main__":
    main()
