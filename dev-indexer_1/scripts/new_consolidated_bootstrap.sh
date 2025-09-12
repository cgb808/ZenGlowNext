#!/usr/bin/env bash
set -euo pipefail
# new_consolidated_bootstrap.sh
# Prepare a clean consolidated (single) Postgres environment without PII split.
# 1. Backup existing .env (if present)
# 2. Generate / augment minimal secrets using collect_secrets.sh
# 3. Remove PII_* lines from .env
# 4. Print next-step commands (compose up + schema sync)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
TS="$(date +%Y%m%d-%H%M%S)"

backup_env() {
  if [[ -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "$ENV_FILE.bak.$TS"
    echo "Backed up existing .env -> .env.bak.$TS" >&2
  fi
}

ensure_collect() {
  if [[ ! -x "$ROOT_DIR/scripts/collect_secrets.sh" ]]; then
    echo "collect_secrets.sh missing or not executable" >&2; exit 2
  fi
}

strip_pii() {
  grep -vE '^(PII_|PII_DATABASE_URL|PII_DATABASE_URL_|DATABASE_URL_TS|DATABASE_URL_VEC|PII_DATABASE_URL_TS|PII_DATABASE_URL_VEC)=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
  mv "$ENV_FILE.tmp" "$ENV_FILE"
}

append_minimal() {
  # Ensure required vars exist; if absent, append placeholders to be replaced by collect script export output.
  for v in POSTGRES_PASSWORD JWT_SECRET; do
    if ! grep -q "^$v=" "$ENV_FILE" 2>/dev/null; then
      echo "$v=__FILL__" >> "$ENV_FILE"
    fi
  done
  if ! grep -q '^DATABASE_URL=' "$ENV_FILE"; then
    echo 'DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/rag_db' >> "$ENV_FILE"
  fi
}

main() {
  backup_env
  touch "$ENV_FILE"
  strip_pii
  append_minimal
  chmod 600 "$ENV_FILE" || true
  echo "Running secret collection (export lines only)." >&2
  # Capture export lines and append sanitized values
  EXPORT_OUT=$(bash "$ROOT_DIR/scripts/collect_secrets.sh" --export-env | grep '^export ')
  while IFS= read -r line; do
    key=$(echo "$line" | cut -d' ' -f2 | cut -d'=' -f1)
    val=$(echo "$line" | sed -E 's/^export [A-Z0-9_]+=//')
    # update or append
    if grep -q "^$key=" "$ENV_FILE"; then
      sed -i "s|^$key=.*|$key=${val}|" "$ENV_FILE"
    else
      echo "$key=${val}" >> "$ENV_FILE"
    fi
  done <<< "$EXPORT_OUT"

  echo "Consolidated .env ready." >&2
  cat <<NEXT
Next steps:
1. Start services: docker compose up -d db redis
2. Apply schemas:   ./scripts/supabase_full_sync.sh --apply (ensure DATABASE_URL points to local db)
3. (Optional) Run verifiers:
     ./scripts/metrics_schema_verify.sh --plan
     ./scripts/dev_kg_schema_verify.sh --plan
4. Start app: docker compose up -d app-dev
5. Later push to cloud: set SUPABASE_DB_URL then run supabase_full_sync.sh --apply --drift-check
NEXT
}

main "$@"
