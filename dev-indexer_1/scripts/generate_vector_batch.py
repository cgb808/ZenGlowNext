#!/usr/bin/env python3
"""
Vector batch generation script for ZenGlow RAG system.

Processes documents and generates embedding vectors using the configured
embedding model, storing results in the vector database.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import json

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy not installed. Run: pip install numpy")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using environment variables."""
    dsn = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
    if not dsn:
        raise ValueError("DATABASE_URL or DB_DSN environment variable required")
    
    logger.info("Connecting to database...")
    return psycopg2.connect(dsn)


def get_embedding_dimension():
    """Get the embedding dimension from environment or use default."""
    return int(os.getenv("PG_EMBED_DIM", "768"))


def fetch_documents_without_vectors(conn, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch documents that don't have embeddings yet."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT dc.id, dc.document_id, dc.chunk_text, dc.chunk_index
            FROM document_chunks dc
            LEFT JOIN chunk_embeddings ce ON dc.id = ce.chunk_id
            WHERE ce.chunk_id IS NULL
            ORDER BY dc.document_id, dc.chunk_index
            LIMIT %s;
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]


def generate_mock_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate a mock embedding vector for development/testing.
    In production, this would use a real embedding model like sentence-transformers.
    """
    # Simple hash-based mock embedding
    import hashlib
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()
    
    # Convert to float values between -1 and 1
    embedding = []
    for i in range(dimension):
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Normalize to [-1, 1] range
        embedding.append((byte_val - 127.5) / 127.5)
    
    return embedding


def store_embeddings(conn, embeddings_data: List[Dict[str, Any]]):
    """Store embeddings in the database."""
    if not embeddings_data:
        return
    
    with conn.cursor() as cur:
        # Insert embeddings
        for item in embeddings_data:
            cur.execute("""
                INSERT INTO chunk_embeddings (chunk_id, embedding_vector, model_name, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (chunk_id) DO UPDATE SET
                    embedding_vector = EXCLUDED.embedding_vector,
                    model_name = EXCLUDED.model_name,
                    updated_at = NOW();
            """, (
                item['chunk_id'],
                item['embedding'],
                item['model_name']
            ))
    
    conn.commit()
    logger.info(f"Stored {len(embeddings_data)} embeddings")


def main():
    """Main vector generation function."""
    batch_size = int(os.getenv("VECTOR_BATCH_SIZE", "50"))
    embedding_dim = get_embedding_dimension()
    model_name = os.getenv("EMBEDDING_MODEL", "mock-embedding-model")
    
    logger.info(f"Starting vector batch generation (batch_size={batch_size}, dim={embedding_dim})")
    
    try:
        with get_db_connection() as conn:
            # Fetch documents without vectors
            docs_to_process = fetch_documents_without_vectors(conn, batch_size)
            
            if not docs_to_process:
                logger.info("No documents need vector generation")
                return
            
            logger.info(f"Processing {len(docs_to_process)} document chunks")
            
            # Generate embeddings
            embeddings_data = []
            for doc in docs_to_process:
                try:
                    # Generate embedding for this chunk
                    embedding = generate_mock_embedding(doc['chunk_text'], embedding_dim)
                    
                    embeddings_data.append({
                        'chunk_id': doc['id'],
                        'embedding': embedding,
                        'model_name': model_name
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {doc['id']}: {e}")
                    continue
            
            # Store all embeddings
            if embeddings_data:
                store_embeddings(conn, embeddings_data)
                logger.info(f"Successfully processed {len(embeddings_data)} embeddings")
            else:
                logger.warning("No embeddings were generated")
                
    except Exception as e:
        logger.error(f"Vector generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
