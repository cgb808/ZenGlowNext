#!/usr/bin/env python3
"""
Batch ingestion script for ZenGlow RAG system.

Ingests documents from various sources into the RAG database,
chunking them appropriately for vector search.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
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


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Simple text chunking with overlap.
    In production, this might use more sophisticated methods.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending punctuation
            for i in range(end, max(start + chunk_size - 100, start), -1):
                if text[i] in '.!?':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start <= 0 or start >= len(text):
            break
    
    return chunks


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def ingest_document(conn, doc_data: Dict[str, Any]) -> Optional[int]:
    """
    Ingest a single document into the database.
    Returns the document ID if successful, None otherwise.
    """
    title = doc_data.get('title', 'Untitled')
    content = doc_data.get('content', '')
    source_url = doc_data.get('source_url')
    family_key = doc_data.get('family_key', 'default')
    
    if not content:
        logger.warning(f"Skipping document '{title}' - no content")
        return None
    
    content_hash = calculate_content_hash(content)
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Check if document already exists
        cur.execute("""
            SELECT id FROM documents 
            WHERE content_hash = %s;
        """, (content_hash,))
        
        existing = cur.fetchone()
        if existing:
            logger.info(f"Document '{title}' already exists (ID: {existing['id']})")
            return existing['id']
        
        # Insert new document
        cur.execute("""
            INSERT INTO documents (
                title, content, source_url, family_key, content_hash, 
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id;
        """, (title, content, source_url, family_key, content_hash))
        
        doc_id = cur.fetchone()['id']
        logger.info(f"Inserted document '{title}' with ID: {doc_id}")
        
        # Chunk the document
        chunks = chunk_text(content)
        logger.info(f"Created {len(chunks)} chunks for document {doc_id}")
        
        # Insert chunks
        for i, chunk_text_content in enumerate(chunks):
            cur.execute("""
                INSERT INTO document_chunks (
                    document_id, chunk_index, chunk_text, 
                    chunk_hash, created_at
                ) VALUES (%s, %s, %s, %s, NOW());
            """, (
                doc_id, 
                i, 
                chunk_text_content, 
                calculate_content_hash(chunk_text_content)
            ))
        
        conn.commit()
        return doc_id


def ingest_from_jsonl(conn, jsonl_path: Path) -> int:
    """
    Ingest documents from a JSONL file.
    Returns the number of documents successfully ingested.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")
    
    success_count = 0
    error_count = 0
    
    logger.info(f"Reading documents from: {jsonl_path}")
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                doc_data = json.loads(line)
                doc_id = ingest_document(conn, doc_data)
                if doc_id:
                    success_count += 1
                else:
                    error_count += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON on line {line_num}: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {e}")
                error_count += 1
    
    logger.info(f"Ingestion complete: {success_count} success, {error_count} errors")
    return success_count


def ingest_sample_documents(conn) -> int:
    """Create some sample documents for testing."""
    sample_docs = [
        {
            "title": "ZenGlow RAG System Overview",
            "content": """ZenGlow is a comprehensive Retrieval-Augmented Generation (RAG) system 
            designed for intelligent document processing and question-answering. The system combines 
            PostgreSQL with pgvector for efficient vector storage, TimescaleDB for time-series data, 
            and advanced embedding models for semantic search. Key features include family-based 
            document organization, conversation tracking, and performance analytics.""",
            "source_url": "internal://zenglow/overview",
            "family_key": "system_docs"
        },
        {
            "title": "Database Schema Guide",
            "content": """The ZenGlow database schema includes several core tables: documents for storing 
            source content, document_chunks for text segments, chunk_embeddings for vector representations, 
            conversation_events for chat history, and document_families for organizational context. 
            The schema leverages PostgreSQL extensions including pgvector for vector operations and 
            TimescaleDB for efficient time-series queries.""",
            "source_url": "internal://zenglow/schema",
            "family_key": "system_docs"
        },
        {
            "title": "Vector Search Implementation",
            "content": """Vector search in ZenGlow uses pgvector's cosine similarity for finding relevant 
            document chunks. The system supports multiple embedding models and includes features like 
            hybrid retrieval combining vector and keyword search, result fusion for improved accuracy, 
            and learning-to-rank models for result optimization. Performance tuning includes proper 
            indexing strategies and query optimization.""",
            "source_url": "internal://zenglow/vector-search",
            "family_key": "technical_docs"
        }
    ]
    
    success_count = 0
    for doc_data in sample_docs:
        try:
            doc_id = ingest_document(conn, doc_data)
            if doc_id:
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to ingest sample document '{doc_data['title']}': {e}")
    
    return success_count


def main():
    """Main ingestion function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents into ZenGlow RAG system")
    parser.add_argument(
        "--jsonl", 
        type=Path, 
        help="Path to JSONL file containing documents to ingest"
    )
    parser.add_argument(
        "--sample", 
        action="store_true", 
        help="Ingest sample documents for testing"
    )
    
    args = parser.parse_args()
    
    if not args.jsonl and not args.sample:
        print("ERROR: Must specify either --jsonl or --sample")
        parser.print_help()
        sys.exit(1)
    
    try:
        with get_db_connection() as conn:
            if args.sample:
                logger.info("Ingesting sample documents...")
                count = ingest_sample_documents(conn)
                logger.info(f"Ingested {count} sample documents")
            
            if args.jsonl:
                logger.info(f"Ingesting from JSONL file: {args.jsonl}")
                count = ingest_from_jsonl(conn, args.jsonl)
                logger.info(f"Ingested {count} documents from JSONL")
                
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
