"""Multi-Database Connection Manager

This module provides a DBManager class responsible for creating and managing
named asynchronous connection pools. It reads various DATABASE_URL environment
variables and creates a pool for each one that is defined.

This allows the application to interact with multiple databases (e.g., for PII
data, specialist agent data, and general data) through a single, consistent
interface.
"""
from __future__ import annotations

from typing import Dict, Optional, Any, List
import os
import asyncio

try:  # Optional dependency; DBManager.startup() will no-op if unavailable
    from psycopg_pool import AsyncConnectionPool  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    AsyncConnectionPool = None  # type: ignore

# Reuse existing async client wrapper (query helpers, etc.)
from .async_db import AsyncDBClient


class DBManager:
    """Manages multiple named asynchronous database connection pools.

    Pools are created eagerly on startup for any configured DSNs found in the
    environment. If pool creation fails for any configured source, startup
    returns False and no pools are retained (best-effort all-or-nothing).
    """

    def __init__(self) -> None:
        # Mapping of logical names -> AsyncConnectionPool
        self.pools: Dict[str, AsyncConnectionPool] = {}  # type: ignore[type-arg]
        # Mapping from logical name to env var containing the DSN
        self.db_sources: Dict[str, str] = {
            "general": "DATABASE_URL",
            "pii": "PII_DATABASE_URL",
            "specialist": "SPECIALIST_DATABASE_URL",
            "secondary": "SECONDARY_DATABASE_URL",  # Optional secondary Postgres
            "cloud": "SUPABASE_DB_URL",  # Cloud instance (e.g., Supabase)
        }
        print("INFO:     [DBManager] Initializing database connection pools...")

    def startup(self) -> bool:
        """Create connection pools for all configured sources.

        Returns True if all configured pools were created and wired in, False otherwise.
        On failure, leaves self.pools unchanged.
        """
        if AsyncConnectionPool is None:
            print("WARN:     [DBManager] psycopg_pool not available; skipping pool startup")
            return False
        temp_pools: Dict[str, AsyncConnectionPool] = {}  # type: ignore[type-arg]
        try:
            min_size = int(os.getenv("DB_POOL_MIN", os.getenv("ASYNC_PG_POOL_MIN", "2")))
            max_size = int(os.getenv("DB_POOL_MAX", os.getenv("ASYNC_PG_POOL_MAX", "10")))
            timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
            for name, env_var in self.db_sources.items():
                dsn = os.getenv(env_var)
                if not dsn:
                    continue
                try:
                    pool = AsyncConnectionPool(  # type: ignore[misc]
                        conninfo=dsn,
                        min_size=min_size,
                        max_size=max_size,
                        timeout=timeout,
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
            # Rollback note: psycopg_pool pools close asynchronously; we log intent.
            for n in list(temp_pools.keys()):
                try:
                    print(f"WARN:     [DBManager] Rolling back pool '{n}' due to startup failure")
                except Exception:
                    pass
            return False

    async def shutdown(self) -> None:
        """Gracefully close all active connection pools."""
        if not self.pools:
            return
        print("INFO:     [DBManager] Closing all database connection pools...")
        for name, pool in self.pools.items():
            try:
                await pool.close()  # type: ignore[union-attr]
                print(f"INFO:     [DBManager] Pool '{name}' closed.")
            except Exception as e:  # pragma: no cover - environment dependent
                print(f"WARN:     [DBManager] Error closing pool '{name}': {e}")

    def get_client(self, name: str = "general") -> Optional[AsyncDBClient]:
        """Get an AsyncDBClient instance for a named database source.

        Args:
            name: Logical db name (e.g., 'general', 'pii', 'specialist').

        Returns:
            AsyncDBClient configured with the pool, or None if not available.
        """
        pool = self.pools.get(name)
        if pool:
            return AsyncDBClient(pool)
        return None

    async def stats(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return per-pool basic stats for specified pool names (best-effort).

        If "include" is None, all available pools are considered. Stats
        collection is best-effort and may return minimal info when unavailable.
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
            pool = self.pools.get(name)
            if not pool:
                return
            # Try a lightweight connectivity probe and collect a couple of attributes
            try:
                client = AsyncDBClient(pool)
                try:
                    # Probe: ensure we can acquire a connection and run SELECT 1
                    await client.execute_query("SELECT 1")
                    ok = True
                except Exception:
                    ok = False
                # Best-effort to read pool attributes (may vary by psycopg version)
                meta: Dict[str, Any] = {"ok": ok}
                for attr in ("min_size", "max_size", "max_waiting"):
                    try:
                        meta[attr] = getattr(pool, attr)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                results[name] = meta
            except Exception:
                results[name] = {"error": "unavailable"}

        await asyncio.gather(*(fetch(n) for n in names))
        return results


__all__ = ["DBManager"]
