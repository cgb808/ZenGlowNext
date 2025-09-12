Legacy utility scripts retained for reference. Not active in current pipeline.

Included:
  - apply_full_schema.py (superseded by db_apply.sh + migrations)
  - transfer_tables_between_dbs.py (rare cross-db ops; use ad-hoc SQL instead)
  - test_dsn.py (replace with pytest-based connectivity test later)
  - pg_notify_to_redis_bridge.py (legacy variant; modern version lives in scripts/)
  - rag_replay_msgpack.py (unchanged functionally; kept original backup)

Preserve for diff / audit only. Remove once parity confirmed.
