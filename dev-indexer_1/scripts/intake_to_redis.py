"""Fast ingestion script: reads source documents, chunks, pushes to Redis list.
Usage:
  python scripts/intake_to_redis.py --source ./source_documents/legal --category legal
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import msgpack  # type: ignore[import-untyped]
import redis  # type: ignore[import-untyped]

SOURCE_DIR_DEFAULT = "./source_documents/legal"
REDIS_HOST_DEFAULT = "localhost"
REDIS_PORT_DEFAULT = 6379
CHUNK_SENTENCES_DEFAULT = 5


def clean_text(text: str) -> str:
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def rough_chunker(text: str, chunk_size_sentences: int = CHUNK_SENTENCES_DEFAULT) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    for s in sentences:
        if not s:
            continue
        current.append(s)
        if len(current) >= chunk_size_sentences:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def push_file(path: Path, r: "redis.Redis", queue_key: str, chunk_size_sentences: int) -> int:  # type: ignore[name-defined]
    raw = path.read_text(encoding="utf-8")
    cleaned = clean_text(raw)
    chunks = rough_chunker(cleaned, chunk_size_sentences)
    pushed = 0
    for i, chunk in enumerate(chunks):
        payload = {
            "source_file": path.name,
            "chunk_id": f"{path.stem}_{i+1}",
            "text": chunk,
            "category": queue_key.split(":", 1)[-1],
        }
        r.rpush(queue_key, msgpack.packb(payload))
        pushed += 1
    return pushed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE_DIR_DEFAULT)
    parser.add_argument("--category", required=True, help="Logical category (used in queue key)")
    parser.add_argument("--redis-host", default=REDIS_HOST_DEFAULT)
    parser.add_argument("--redis-port", type=int, default=REDIS_PORT_DEFAULT)
    parser.add_argument("--chunk-sentences", type=int, default=CHUNK_SENTENCES_DEFAULT)
    args = parser.parse_args()

    queue_key = f"intake_queue:{args.category}"
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Source directory not found: {source_path}")
        return
    print(f"→ Connecting to Redis {args.redis_host}:{args.redis_port} ...")
    try:
        r = redis.Redis(host=args.redis_host, port=args.redis_port, db=0, decode_responses=False)  # type: ignore[call-arg]
        r.ping()
    except Exception as e:  # pragma: no cover
        print(f"❌ Redis connection failed: {e}")
        return
    total = 0
    if source_path.is_file():
        # Single file processing
        print(f"  Processing {source_path.name}")
        total += push_file(source_path, r, queue_key, args.chunk_sentences)  # type: ignore[arg-type]
    else:
        # Directory processing
        for path in sorted(source_path.glob("*.txt")):
            print(f"  Processing {path.name}")
            total += push_file(path, r, queue_key, args.chunk_sentences)  # type: ignore[arg-type]
    print(f"✅ Done. Pushed {total} chunks to queue {queue_key}")


if __name__ == "__main__":  # pragma: no cover
    main()
