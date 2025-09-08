"""Background worker: polls Redis queues, batches, inserts into Postgres.
Usage:
  python scripts/batch_writer_from_redis.py --queues legal medical
"""
from __future__ import annotations
import argparse
import json
import os
import time
import msgpack  # type: ignore
import psycopg2  # type: ignore
import psycopg2.extras  # type: ignore
import redis  # type: ignore
from typing import Sequence

REDIS_HOST_DEFAULT = "localhost"
REDIS_PORT_DEFAULT = 6379
BATCH_SIZE_DEFAULT = 100
IDLE_INTERVAL_DEFAULT = 10
MAX_IDLE_CYCLES_DEFAULT = 60  # Exit after 60 idle cycles (10 minutes with 10s intervals)
PG_CONN_ENV = "PG_CONN_STRING"

INSERT_SQL = """
INSERT INTO documents (chunk_id, content, source, category, weight, priority, sidecar_metadata, file_metadata, source_config, timestamp)
VALUES %s
ON CONFLICT (chunk_id) DO NOTHING;
"""


def fetch_batch(r: redis.Redis, queue_key: str, batch_size: int):  # type: ignore[name-defined]
    pipe = r.pipeline()
    pipe.lrange(queue_key, 0, batch_size - 1)
    pipe.ltrim(queue_key, batch_size, -1)
    items, _ = pipe.execute()
    return items or []


def process_items(raw_items) -> list[tuple[str, str, str, str, float, str, str, str, str, float]]:
    out = []
    for raw in raw_items:
        try:
            data = msgpack.unpackb(raw)
            out.append(
                (
                    data["chunk_id"],
                    data["text"],
                    data["source_file"],
                    data["category"],
                    data.get("weight", 0.5),
                    data.get("priority", "medium"),
                    json.dumps(data.get("sidecar_metadata", {})),
                    json.dumps(data.get("file_metadata", {})),
                    json.dumps(data.get("source_config", {})),
                    data.get("timestamp", 0.0)
                )
            )
        except Exception as e:  # pragma: no cover
            print(f"⚠️  Skipping corrupt item: {e}")
    return out


def bulk_insert(conn_string: str, records: Sequence[tuple[str, str, str, str, float, str, str, str, str, float]]):
    if not records:
        return 0
    with psycopg2.connect(conn_string) as conn:  # type: ignore[arg-type]
        with conn.cursor() as cur:  # type: ignore[call-arg]
            psycopg2.extras.execute_values(cur, INSERT_SQL, records)
            return len(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default=REDIS_HOST_DEFAULT)
    parser.add_argument("--redis-port", type=int, default=REDIS_PORT_DEFAULT)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT)
    parser.add_argument("--idle-seconds", type=int, default=IDLE_INTERVAL_DEFAULT)
    parser.add_argument("--max-idle-cycles", type=int, default=MAX_IDLE_CYCLES_DEFAULT, 
                        help="Exit after this many consecutive idle cycles (0 = run forever)")
    parser.add_argument("--queues", nargs="+", required=True, help="Category queue names (e.g. legal medical)")
    parser.add_argument("--pg-conn", default=os.getenv(PG_CONN_ENV, ""), help="Postgres connection string (or set PG_CONN_STRING env var)")
    args = parser.parse_args()

    if not args.pg_conn:
        print("❌ Missing Postgres connection string (use --pg-conn or PG_CONN_STRING env var)")
        return

    queues = [f"intake_queue:{q}" for q in args.queues]

    print(f"→ Connecting to Redis {args.redis_host}:{args.redis_port}")
    try:
        r: redis.Redis = redis.Redis(host=args.redis_host, port=args.redis_port, db=0, decode_responses=False)  # type: ignore[assignment]
        r.ping()
    except Exception as e:  # pragma: no cover
        print(f"❌ Redis connection failed: {e}")
        return

    print(f"→ Watching queues: {', '.join(queues)} (batch={args.batch_size})")
    if args.max_idle_cycles > 0:
        print(f"→ TTL: Will exit after {args.max_idle_cycles} idle cycles ({args.max_idle_cycles * args.idle_seconds} seconds)")
    
    idle_cycle_count = 0
    
    while True:
        cycle_total = 0
        for q in queues:
            size = r.llen(q)  # type: ignore[attr-defined]
            if size >= args.batch_size:
                print(f"  {q}: size={size} taking {args.batch_size}")
                raw_items = fetch_batch(r, q, args.batch_size)
                records = process_items(raw_items)
                inserted = bulk_insert(args.pg_conn, records)
                cycle_total += inserted
                if inserted:
                    print(f"    ✅ Inserted {inserted} records")
        
        if cycle_total > 0:
            # Reset idle counter when we process data
            idle_cycle_count = 0
        else:
            # Increment idle counter
            idle_cycle_count += 1
            print(f"(idle {args.idle_seconds}s) … [{idle_cycle_count}/{args.max_idle_cycles if args.max_idle_cycles > 0 else '∞'}]")
            
            # Check TTL exit condition
            if args.max_idle_cycles > 0 and idle_cycle_count >= args.max_idle_cycles:
                print(f"🔄 TTL reached: Exiting after {idle_cycle_count} idle cycles")
                break
                
            time.sleep(args.idle_seconds)


if __name__ == "__main__":  # pragma: no cover
    main()
