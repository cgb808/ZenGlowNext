#!/usr/bin/env python3
"""
Database initialization script for ZenGlow RAG system.

Reads the consolidated schema and sets up the database with all required tables,
extensions, and TimescaleDB hypertables.
"""

import os
import sys
import logging
from pathlib import Path

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
    
    logger.info(f"Connecting to database...")
    return psycopg2.connect(dsn)


def read_schema_file(schema_path: Path) -> str:
    """Read the SQL schema file."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    logger.info(f"Reading schema from: {schema_path}")
    return schema_path.read_text()


def execute_schema(conn, schema_sql: str):
    """Execute the schema SQL."""
    logger.info("Executing schema SQL...")
    
    with conn.cursor() as cur:
        # Execute the full schema
        try:
            cur.execute(schema_sql)
            conn.commit()
            logger.info("Schema executed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Schema execution failed: {e}")
            raise


def verify_installation(conn):
    """Verify that key tables and extensions are installed."""
    logger.info("Verifying installation...")
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Check extensions
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'timescaledb');")
        extensions = [row['extname'] for row in cur.fetchall()]
        logger.info(f"Extensions installed: {extensions}")
        
        # Check key tables
        key_tables = [
            'documents', 'document_chunks', 'conversation_events', 
            'document_families', 'family_artifacts', 'rag_performance'
        ]
        
        for table in key_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            exists = cur.fetchone()['exists']
            logger.info(f"Table '{table}': {'✓' if exists else '✗'}")
        
        # Check hypertables (TimescaleDB)
        cur.execute("""
            SELECT hypertable_schema, hypertable_name 
            FROM timescaledb_information.hypertables 
            WHERE hypertable_schema = 'public';
        """)
        hypertables = [row['hypertable_name'] for row in cur.fetchall()]
        logger.info(f"Hypertables: {hypertables}")


def main():
    """Main initialization function."""
    # Find schema file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    schema_path = project_root / "sql" / "consolidated_rag_schema_v2.sql"
    
    if not schema_path.exists():
        # Try alternative locations
        alt_paths = [
            project_root / "sql" / "consolidated_rag_schema.sql",
            project_root / "schema.sql",
            script_dir / "schema.sql"
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                schema_path = alt_path
                break
        else:
            logger.error(f"Schema file not found. Tried: {schema_path}")
            logger.error("Please ensure the SQL schema file exists")
            sys.exit(1)
    
    try:
        # Read schema
        schema_sql = read_schema_file(schema_path)
        
        # Connect and execute
        with get_db_connection() as conn:
            execute_schema(conn, schema_sql)
            verify_installation(conn)
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
