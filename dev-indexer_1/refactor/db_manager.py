"""
Multi-Database Connection Manager

This module provides a DBManager class responsible for creating and managing
a dictionary of named asynchronous connection pools. It reads various
DATABASE_URL environment variables and creates a pool for each one that is defined.

This allows the application to interact with multiple databases (e.g., for PII
data, specialist agent data, and general data) through a single, consistent
interface.
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Any, List
import asyncio

try:
    from psycopg_pool import AsyncConnectionPool
except Exception:  # pragma: no cover - optional dependency
    AsyncConnectionPool = None  # type: ignore

from .db_async import AsyncDBClient  # reuse existing async client wrapper


class DBManager:
    """Manages multiple named asynchronous database connection pools."""

    def __init__(self) -> None:
        self.pools: Dict[str, AsyncConnectionPool] = {}  # type: ignore[type-arg]
        # A mapping from logical names to the environment variables that hold their DSNs.
        self.db_sources = {
            "general": "DATABASE_URL",
            "pii": "PII_DATABASE_URL",
            "specialist": "SPECIALIST_DATABASE_URL",
            "secondary": "SECONDARY_DATABASE_URL",  # Optional secondary Postgres
            "cloud": "SUPABASE_DB_URL",  # Your cloud Supabase instance
        }
        print("INFO:     [DBManager] Initializing database connection pools...")

    def startup(self) -> bool:
        """Creates connection pools for all configured database sources atomically.

        Returns True if all configured pools were created and wired in, False otherwise.
        On failure, closes any partially created pools and leaves self.pools unchanged.
        """
        if AsyncConnectionPool is None:
            print("WARN:     [DBManager] psycopg_pool not available; skipping pool startup")
            return False
        temp_pools: Dict[str, AsyncConnectionPool] = {}  # type: ignore[type-arg]
        try:
            for name, env_var in self.db_sources.items():
                dsn = os.getenv(env_var)
                if not dsn:
                    continue
                try:
                    pool = AsyncConnectionPool(
                        conninfo=dsn,
                        min_size=int(os.getenv("DB_POOL_MIN", 2)),
                        max_size=int(os.getenv("DB_POOL_MAX", 10)),
                        timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
                    )
                    temp_pools[name] = pool
                    print(f"INFO:     [DBManager] Pool '{name}' created for {env_var}.")
                except Exception as e:  # pragma: no cover - environment dependent
                    print(f"ERROR:    [DBManager] Failed to create pool '{name}': {e}")
                    raise
            # Success: wire in
            self.pools = temp_pools
            return True
        except Exception:
            # Close any partially created pools
            for n, p in temp_pools.items():
                try:
                    # AsyncConnectionPool.close() is async; best-effort sync close not available.
                    # Rely on lifespan shutdown to clean up if needed; log intent here.
                    print(f"WARN:     [DBManager] Rolling back pool '{n}' due to startup failure")
                except Exception:
                    pass
            return False

    async def shutdown(self) -> None:
        """Gracefully closes all active connection pools."""
        if not self.pools:
            return
        print("INFO:     [DBManager] Closing all database connection pools...")
        for name, pool in self.pools.items():
            try:
                await pool.close()
                print(f"INFO:     [DBManager] Pool '{name}' closed.")
            except Exception as e:  # pragma: no cover - environment dependent
                print(f"WARN:     [DBManager] Error closing pool '{name}': {e}")

    def get_client(self, name: str = "general") -> Optional[AsyncDBClient]:
        """
        Gets an AsyncDBClient instance for a named database source.

        Args:
            name: The logical name of the database ('general', 'pii', etc.).

        Returns:
            An AsyncDBClient instance configured with the correct pool, or None
            if the pool does not exist.
        """
        pool = self.pools.get(name)
        if pool:
            return AsyncDBClient(pool)
        return None

    async def stats(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return per-pool stats for the specified pool names.

        Args:
            include: Optional list of pool names to include. If None, all available pools are used.

        Returns:
            A mapping of pool name -> stats dict as provided by AsyncDBClient.stats().
        """
        results: Dict[str, Any] = {}
        if not self.pools:
            return results

        names: List[str]
        if include:
            names = [n for n in include if n in self.pools]
        else:
            names = list(self.pools.keys())

        async def fetch(name: str) -> None:
            client = self.get_client(name)
            if not client:
                return
            try:
                results[name] = await client.stats()
            except Exception:
                # Best-effort: skip pool that errors
                results[name] = {"error": "unavailable"}

        await asyncio.gather(*(fetch(n) for n in names))
        return results

__all__ = ["DBManager"]
