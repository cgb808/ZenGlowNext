#!/usr/bin/env bash
set -euo pipefail

# Ingestion wrapper for MessagePack replay into Postgres
# Moves files across spool phases and invokes the Python replayer.

# --- Configuration (env-overridable) ---
SPOOL_DIR=${SPOOL_DIR:-"./data/spool"}
INCOMING_DIR="${SPOOL_DIR}/incoming"
PROCESSING_DIR="${SPOOL_DIR}/processing"
ARCHIVE_DIR="${SPOOL_DIR}/archive"
FAILED_DIR="${SPOOL_DIR}/failed"

PYTHON_REPLAY_SCRIPT=${PYTHON_REPLAY_SCRIPT:-"./scripts/rag_replay_msgpack.py"}
PYTHON_MANIFEST_HELPER=${PYTHON_MANIFEST_HELPER:-"./scripts/ingestion_manifest.py"}
RAG_LOG_FILE=${RAG_LOG_FILE:-"./logs/rag_ingestion.log"}

# Optional Go notifier integration
NOTIFIER_BIN=${NOTIFIER_BIN:-"./bin/notifier"}
NOTIFIER_TPL_OPEN=${NOTIFIER_TPL_OPEN:-"./tools/notifier/templates/gate_open.json.tmpl"}
NOTIFIER_TPL_DONE=${NOTIFIER_TPL_DONE:-"./tools/notifier/templates/gate_done.json.tmpl"}
NOTIFIER_TPL_EMBED_START=${NOTIFIER_TPL_EMBED_START:-"./tools/notifier/templates/embed_start.json.tmpl"}

# Optional PII gate integration (managed in PII DB)
PII_GATE=${PII_GATE:-"1"}                   # enable by default if PII_DATABASE_URL set
PII_GATE_HELPER=${PII_GATE_HELPER:-"./scripts/pii_gate.py"}

mkdir -p "${INCOMING_DIR}" "${PROCESSING_DIR}" "${ARCHIVE_DIR}" "${FAILED_DIR}" \
         "$(dirname "${RAG_LOG_FILE}")"

echo "----------------------------------------" | tee -a "${RAG_LOG_FILE}"
echo "Starting ingestion run at $(date -Is)" | tee -a "${RAG_LOG_FILE}"

# Atomically move pending .msgpack files into processing
shopt -s nullglob
pending=("${INCOMING_DIR}"/*.msgpack)
if (( ${#pending[@]} == 0 )); then
  echo "No new files to process." | tee -a "${RAG_LOG_FILE}"
  exit 0
fi
for f in "${pending[@]}"; do
  mv -f "$f" "${PROCESSING_DIR}/"
done
echo "Moved ${#pending[@]} files to ${PROCESSING_DIR}." | tee -a "${RAG_LOG_FILE}"

# Compute batch tag and manifest info
BATCH_TAG=${BATCH_TAG:-"spool_$(date +%Y%m%d_%H%M%S)"}
total_bytes=0
file_names=()
for f in "${PROCESSING_DIR}"/*.msgpack; do
  [[ -e "$f" ]] || break
  file_names+=("$(basename "$f")")
  (( total_bytes += $(stat -c%s "$f") )) || true
done

# Create PII gate lock (optional)
if [[ "${PII_GATE}" = "1" && -n "${PII_DATABASE_URL:-}" && -x "${PII_GATE_HELPER}" ]]; then
  python3 "${PII_GATE_HELPER}" ensure --batch-tag "${BATCH_TAG}" || true
fi

# Notify gate open (optional)
if [[ -x "${NOTIFIER_BIN}" && -f "${NOTIFIER_TPL_OPEN}" ]]; then
  count=${#file_names[@]}
  data=$(python3 - <<PY
import json
print(json.dumps({
  "batch_tag": "${BATCH_TAG}",
  "spool": "${PROCESSING_DIR}",
  "bytes": ${total_bytes},
  "count": ${count}
}))
PY
)
  "${NOTIFIER_BIN}" -template "${NOTIFIER_TPL_OPEN}" -data "${data}" -v || true
fi

# Pre-create/mark manifest queued
if [[ -n "${DATABASE_URL:-}" || -n "${SUPABASE_DB_URL:-}" ]]; then
  python3 - <<PY
from ingestion_manifest import create_or_update_manifest
create_or_update_manifest(
    batch_tag="${BATCH_TAG}",
    files=${file_names[@]+file_names},
    total_bytes=${total_bytes},
    status="processing",
    extra={"spool_dir": "${PROCESSING_DIR}"},
)
PY
fi

# Run Python ingestion with skip-existing for idempotency
set +e
python3 "${PYTHON_REPLAY_SCRIPT}" \
  --glob "${PROCESSING_DIR}/*.msgpack" \
  --skip-existing \
  >> "${RAG_LOG_FILE}" 2>&1
EXIT_CODE=$?
set -e

if [[ ${EXIT_CODE} -eq 0 ]]; then
  echo "Ingestion successful. Archiving processed files." | tee -a "${RAG_LOG_FILE}"
  for f in "${PROCESSING_DIR}"/*.msgpack; do
    [[ -e "$f" ]] || break
    mv -f "$f" "${ARCHIVE_DIR}/"
  done
  # Mark manifest success
  if [[ -n "${DATABASE_URL:-}" || -n "${SUPABASE_DB_URL:-}" ]]; then
    python3 - <<PY
from ingestion_manifest import finish_manifest
finish_manifest(batch_tag="${BATCH_TAG}", status="success")
PY
  fi
  # Open PII gate (optional)
  if [[ "${PII_GATE}" = "1" && -n "${PII_DATABASE_URL:-}" && -x "${PII_GATE_HELPER}" ]]; then
    python3 "${PII_GATE_HELPER}" open --batch-tag "${BATCH_TAG}" || true
  fi
  # Notify gate done success (optional)
  if [[ -x "${NOTIFIER_BIN}" && -f "${NOTIFIER_TPL_DONE}" ]]; then
    processed=$(ls -1 "${ARCHIVE_DIR}"/*.msgpack 2>/dev/null | wc -l | awk '{print $1}')
    data=$(python3 - <<PY
import json
print(json.dumps({
  "batch_tag": "${BATCH_TAG}",
  "status": "success",
  "processed": ${processed}
}))
PY
)
    "${NOTIFIER_BIN}" -template "${NOTIFIER_TPL_DONE}" -data "${data}" -v || true
  fi
  # Trigger embed.start publish (optional)
  if [[ -x "${NOTIFIER_BIN}" && -f "${NOTIFIER_TPL_EMBED_START}" ]]; then
    data=$(python3 - <<PY
import json
print(json.dumps({"batch_tag": "${BATCH_TAG}"}))
PY
)
    "${NOTIFIER_BIN}" -template "${NOTIFIER_TPL_EMBED_START}" -data "${data}" -v || true
  fi
  # Optional Redis publish (JSON)
  if [[ -n "${REDIS_URL:-}" || -n "${REDIS_HOST:-}" ]]; then
    python3 - <<'PY'
import json, os, sys
from datetime import datetime, timezone
try:
    import redis  # type: ignore
except Exception:
    sys.exit(0)

host = os.getenv("REDIS_HOST", "localhost")
port = int(os.getenv("REDIS_PORT", "6379"))
db = int(os.getenv("REDIS_DB", "0"))
password = os.getenv("REDIS_PASSWORD")
ch = os.getenv("REDIS_BUILD_CHANNEL", "build_updates")
r = redis.Redis(host=host, port=port, db=db, password=password)
evt = {
    "type": "ingest.ready",
    "encoding": os.getenv("REDIS_PUBSUB_FORMAT", "json"),
    "content": {"batch_tag": os.getenv("BATCH_TAG"), "status": "success"},
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
r.publish(ch, json.dumps(evt))
PY
  fi
else
  echo "Ingestion FAILED with exit code ${EXIT_CODE}. Moving files to ${FAILED_DIR}." | tee -a "${RAG_LOG_FILE}"
  for f in "${PROCESSING_DIR}"/*.msgpack; do
    [[ -e "$f" ]] || break
    mv -f "$f" "${FAILED_DIR}/"
  done
  if [[ -n "${DATABASE_URL:-}" || -n "${SUPABASE_DB_URL:-}" ]]; then
    python3 - <<PY
from ingestion_manifest import finish_manifest
finish_manifest(batch_tag="${BATCH_TAG}", status="failed", error="ingestion script failed")
PY
  fi
  # Notify gate done failure (optional)
  if [[ -x "${NOTIFIER_BIN}" && -f "${NOTIFIER_TPL_DONE}" ]]; then
    failed=$(ls -1 "${FAILED_DIR}"/*.msgpack 2>/dev/null | wc -l | awk '{print $1}')
    data=$(python3 - <<PY
import json
print(json.dumps({
  "batch_tag": "${BATCH_TAG}",
  "status": "failed",
  "processed": ${failed}
}))
PY
)
    "${NOTIFIER_BIN}" -template "${NOTIFIER_TPL_DONE}" -data "${data}" -v || true
  fi
fi

echo "Ingestion run finished at $(date -Is)" | tee -a "${RAG_LOG_FILE}"
echo "----------------------------------------" | tee -a "${RAG_LOG_FILE}"
