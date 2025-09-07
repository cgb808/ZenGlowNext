#!/usr/bin/env bash
set -euo pipefail

# github_pat_check.sh - Validate presence & minimal scopes of GITHUB_PAT
# Usage: source .env (or export GITHUB_PAT) then run: bash scripts/github_pat_check.sh
# Exits non-zero if token missing or appears invalid.

if [[ "${GITHUB_PAT:-}" == "" ]]; then
  echo "[error] GITHUB_PAT not set. Export it or put it in your .env file." >&2
  exit 1
fi

# Basic format check (classic tokens start with ghp_, fine-grained with github_pat_)
if ! [[ $GITHUB_PAT =~ ^gh(p|o|u|s)_ || $GITHUB_PAT == github_pat_* ]]; then
  echo "[warn] GITHUB_PAT does not match common prefix (ghp_/github_pat_). Continuing anyway." >&2
fi

API=https://api.github.com/user
# We request only rate limit + user login to confirm validity
resp=$(curl -s -H "Authorization: token $GITHUB_PAT" -H 'Accept: application/vnd.github+json' "$API") || {
  echo "[error] curl failed hitting GitHub API" >&2; exit 2; }

login=$(echo "$resp" | jq -r '.login // empty' 2>/dev/null || true)
message=$(echo "$resp" | jq -r '.message // empty' 2>/dev/null || true)

if [[ -z "$login" ]]; then
  echo "[error] Could not validate token (message: $message)." >&2
  echo "$resp" | sed 's/\"/"/g' >&2
  exit 3
fi

echo "[ok] GitHub token valid for user: $login"

# Optional: check scopes (only available in headers); perform a HEAD request to capture x-oauth-scopes
scopes=$(curl -s -D - -o /dev/null -H "Authorization: token $GITHUB_PAT" -H 'Accept: application/vnd.github+json' "$API" | awk -F': ' '/^x-oauth-scopes:/ {print $2}' | tr -d '\r') || true
if [[ -n "$scopes" ]]; then
  echo "[info] Token scopes: $scopes"
  # Minimal recommended: repo, read:org (adjust per needs)
  missing=()
  for req in repo read:org; do
    if ! grep -qi "\b$req\b" <<< "$scopes"; then
      missing+=("$req")
    fi
  done
  if (( ${#missing[@]} > 0 )); then
    echo "[warn] Missing recommended scopes: ${missing[*]}" >&2
  fi
else
  echo "[info] Could not determine scopes (GitHub may omit header for some token types)."
fi

exit 0
