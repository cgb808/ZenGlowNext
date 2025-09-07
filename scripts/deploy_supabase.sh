#!/usr/bin/env bash
set -euo pipefail

if ! command -v supabase >/dev/null 2>&1; then
  echo "[deploy] Supabase CLI not found. Install: https://supabase.com/docs/guides/cli" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <PROJECT_REF> [MODEL_URL] [MODEL_NAME] [ALLOW_ORIGIN]" >&2
  exit 1
fi

PROJECT_REF=$1
MODEL_URL=${2:-"http://127.0.0.1:11434"}
MODEL_NAME=${3:-"gemma:2b"}
ALLOW_ORIGIN=${4:-"*"}

echo "[deploy] Linking project $PROJECT_REF"
(supabase link --project-ref "$PROJECT_REF" >/dev/null || true)

echo "[deploy] Pushing migrations"
supabase db push

echo "[deploy] Setting secrets"
supabase secrets set MODEL_URL="$MODEL_URL" MODEL_NAME="$MODEL_NAME" ALLOW_ORIGIN="$ALLOW_ORIGIN"

if [ -d "supabase/functions/llm" ]; then
  echo "[deploy] Deploying Edge Function: llm"
  supabase functions deploy llm
  TEST_PATH=llm
elif [ -d "supabase/functions/llm-proxy" ]; then
  echo "[deploy] Deploying Edge Function: llm-proxy (legacy)"
  supabase functions deploy llm-proxy
  TEST_PATH=llm-proxy
else
  echo "[deploy] No llm or llm-proxy directory present" >&2
  TEST_PATH="llm"
fi

# Deploy curate-code ingestion function if present
if [ -d "supabase/functions/curate-code" ]; then
  echo "[deploy] Deploying Edge Function: curate-code"
  supabase functions deploy curate-code || echo "[deploy][warn] curate-code deploy failed"
fi

echo "[deploy] Done. Test with:"
echo "curl -s -X POST -H 'Content-Type: application/json' -d '{\"prompt\":\"Hello?\"}' https://$PROJECT_REF.functions.supabase.co/$TEST_PATH"
