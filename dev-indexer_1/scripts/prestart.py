"""Prestart helper to ensure .env has all keys from .env.example without overwriting.

- Merges .env.example -> .env (adds missing keys only)
- Then loads .env.local and .env into process env (without overwriting existing)

This can be used in docker-compose or local dev before starting the app.
"""

from __future__ import annotations

from scripts.env_load import load_env_files
from scripts.merge_env import merge_env


def main() -> None:
    try:
        added = merge_env(".env.example", ".env")
        print(f"merge_env: added {added} keys to .env (preserved existing)")
    except Exception as e:
        print(f"merge_env skipped: {e}")
    try:
        loaded = load_env_files([".env.local", ".env"])  # no overwrite
        print(f"env_load: loaded {loaded} keys (without overwriting)")
    except Exception as e:
        print(f"env_load skipped: {e}")


if __name__ == "__main__":
    main()
