#!/usr/bin/env bash
# precommit_pii_guard.sh
# Enforces presence of PII classification comment markers for newly added
# potentially sensitive columns in staged Supabase migration SQL files.
# Blocks commit if heuristic-detected PII columns lack a matching tagged COMMENT.
#
# Markers (case-insensitive): [PII] [SENSITIVE] [RESTRICTED] or explicit [NONPII]
# Bypass (not recommended): export ALLOW_UNTAGGED_PII=1

set -euo pipefail

MARKERS='\[(PII|SENSITIVE|RESTRICTED|NONPII)\]'
PII_NAME_REGEX='(email|e_mail|phone|mobile|address|addr|lat|lon|ip(_addr)?|ssn|dob|birth|first_name|last_name|fullname|name|user_id|geo|location)'

if [[ "${ALLOW_UNTAGGED_PII:-}" == 1 ]]; then
  echo "[pii-guard] Bypass enabled (ALLOW_UNTAGGED_PII=1)." >&2
  exit 0
fi

# Gather staged migration files (added/modified)
mapfile -t FILES < <(git diff --cached --name-only --diff-filter=ACM | grep -E '^supabase/migrations/.*\.sql$' || true)
[[ ${#FILES[@]} -eq 0 ]] && exit 0

FAIL=0
for f in "${FILES[@]}"; do
  content=$(git show ":$f")
  # Collect candidate column names from CREATE TABLE or ADD COLUMN lines
  # Pattern: <name> <type> ...
  mapfile -t candidates < <(printf '%s' "$content" | \
    grep -Ei "(create table|add column)" | \
    grep -Eo '([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]+[a-zA-Z]' | \
    awk '{print $1}' | sort -u | grep -Ei "$PII_NAME_REGEX" || true)
  [[ ${#candidates[@]} -eq 0 ]] && continue

  # For each candidate, ensure a matching COMMENT ON (column or table) containing marker exists
  for col in "${candidates[@]}"; do
    # Accept either column-level COMMENT ON COLUMN ... col ... or table-level marker in same file.
    if printf '%s' "$content" | grep -Ei "COMMENT ON (COLUMN|TABLE)" | grep -Fi "$col" | grep -Eqi "$MARKERS"; then
      continue
    fi
    # Table-level comment may apply: if any table comment contains marker AND table contains column.
    # (Simplistic: just check marker existence in any TABLE comment.)
    if printf '%s' "$content" | grep -Ei "COMMENT ON TABLE" | grep -Eqi "$MARKERS"; then
      continue
    fi
    echo "[pii-guard] $f -> column '$col' appears PII-like but lacks classification COMMENT (add one with [PII]/[SENSITIVE]/[RESTRICTED] or [NONPII])." >&2
    FAIL=1
  done
done

if [[ $FAIL -ne 0 ]]; then
  echo "[pii-guard] Commit blocked. Tag suspected columns. Override with ALLOW_UNTAGGED_PII=1 (not recommended)." >&2
  exit 1
fi

exit 0
