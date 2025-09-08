#!/usr/bin/env bash
set -euo pipefail

# Launch (or resume) a local Supabase stack (including Studio UI) using the Supabase CLI.
# This does NOT replace the existing project docker-compose; it runs in a separate
# supabase-managed docker network. Use it for:
#   - Browsing & editing schema via Studio
#   - Testing RLS / policies interactively
#   - Trying auth/storage/realtime locally
#
# Requirements:
#   supabase CLI installed & logged in (supabase login) – login optional for local only.
#
# Ports (CLI defaults; may differ if already in use):
#   Studio:          http://localhost:54323
#   REST (PostgREST): http://localhost:54321
#   Auth (GoTrue):    http://localhost:9999
#   Meta API:         http://localhost:8080
#   Realtime:         ws://localhost:54322
#   DB:               localhost:54322 (internal to supabase cluster)
#
# If you want Studio to inspect your existing project Postgres (rag_postgres_db),
# you can: dump & restore OR point migrations at your codebase and apply inside
# the Supabase stack. Easiest for review: pg_dump -> psql import into the Supabase
# stack's database (see at bottom).

echo "[studio] Checking supabase CLI availability"
if ! command -v supabase >/dev/null 2>&1; then
  echo "supabase CLI not found. Install: https://supabase.com/docs/guides/cli" >&2
  exit 1
fi

STATUS=$(supabase status 2>/dev/null || true)
if echo "$STATUS" | grep -qi "supabase local development setup is running"; then
  echo "[studio] Supabase stack already running. Opening status summary:" >&2
  echo "$STATUS"
else
  echo "[studio] Starting Supabase local stack (this can take ~1-2 minutes first run)" >&2
  supabase start
fi

echo "[studio] Studio URL: http://localhost:54323" >&2
echo "[studio] REST endpoint: http://localhost:54321" >&2
echo "[studio] To stop later: supabase stop" >&2

cat <<'EOF'

Import existing project DB into Supabase stack (optional):
  # From existing project container -> dump
  docker exec -t rag_postgres_db pg_dump -U postgres -d rag_db > /tmp/rag_db_dump.sql
  # Into Supabase stack DB (default password: postgres / db: postgres)
  psql postgres://postgres:postgres@localhost:54322/postgres -f /tmp/rag_db_dump.sql

NOTE: Replace credentials if you changed defaults in ~/.supabase/config.toml.
EOF
