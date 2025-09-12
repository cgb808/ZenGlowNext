# Apply Hybrid Retrieval schema to the configured Postgres DB
.PHONY: db-apply-hybrid
db-apply-hybrid:
	@echo "[db] Applying hybrid retrieval schema..."
	@./scripts/sql/run_psql.sh scripts/SQL/sql/hybrid_retrieval_schema.sql
	@echo "[db] Done."

########################################
# ZenGlow RAG Dev Workflow Makefile
########################################

PYTHON ?= python
PIP ?= pip
API_PORT ?= 8000

.DEFAULT_GOAL := help

## ---- Helper ----
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed -e 's/:.*##/\t-/' | sort

## ---- Environment ----
venv: ## Create virtual environment (.venv) if missing
	@if [ -d .venv ]; then echo ".venv already exists"; else $(PYTHON) -m venv .venv || true; fi

setup: venv ## Install runtime + dev deps (no torch specialization)
	. .venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt -r requirements-dev.txt

freeze: ## Export resolved dependencies (runtime only)
	. .venv/bin/activate && pip freeze > requirements.lock

deps-gpu-or-cpu: ## GPU-first dependency install with CPU torch fallback
	@set -e; \
	if [ ! -d .venv ]; then echo "Creating venv"; $(PYTHON) -m venv .venv; fi; \
	. .venv/bin/activate; \
	pip install --upgrade pip setuptools wheel; \
	if command -v nvidia-smi >/dev/null 2>&1; then \
	  echo "[deps] GPU detected -> installing requirements (torch will resolve GPU build)"; \
	  pip install -r requirements.txt; \
	else \
	  echo "[deps] No GPU detected -> installing CPU torch first"; \
	  pip install --force-reinstall --index-url https://download.pytorch.org/whl/cpu torch; \
	  pip install -r requirements.txt; \
	fi; \
	pip install -r requirements-dev.txt; \
	python -c 'import fastapi, torch, transformers; print("[deps] Smoke import OK")'

train-deps: ## Install extended training deps (requirements-train.txt)
	@if [ ! -d .venv ]; then $(PYTHON) -m venv .venv; fi; \
	. .venv/bin/activate; \
	pip install --upgrade pip setuptools wheel; \
	pip install -r requirements-train.txt; \
	echo "[train-deps] Installed training extensions"

asr-train-deps: ## Install full ASR training deps (runtime + train extras)
	@if [ ! -d .venv ]; then $(PYTHON) -m venv .venv; fi; \
	. .venv/bin/activate; \
	pip install --upgrade pip setuptools wheel; \
	pip install -r requirements-all.txt; \
	python -c 'import datasets, soundfile; print("[asr-train-deps] OK")'

deps-all: ## Install unified full stack deps (runtime + train + dev) via requirements-all.txt
	@if [ ! -d .venv ]; then $(PYTHON) -m venv .venv; fi; \
	. .venv/bin/activate; \
	pip install --upgrade pip setuptools wheel; \
	pip install -r requirements-all.txt; \
	python -c 'import fastapi, torch, transformers; print("[deps-all] Smoke import OK")'

deps-cpu-slim: ## Rebuild single CPU-only slim env (removes existing .venv) skipping GPU libs & bitsandbytes
	@echo "[cpu-slim] Removing existing .venv (if any)"; rm -rf .venv; \
	$(PYTHON) -m venv .venv; \
	. .venv/bin/activate; \
	pip install --upgrade pip setuptools wheel; \
	echo "[cpu-slim] Installing CPU torch stack"; \
	pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchaudio; \
	echo "[cpu-slim] Building filtered training requirements (skip bitsandbytes)"; \
	grep -v '^bitsandbytes' requirements-train.txt > .cpu-train.tmp; \
	echo "[cpu-slim] Installing runtime + dev + filtered train"; \
	pip install -r requirements.txt -r requirements-dev.txt -r .cpu-train.tmp; \
	rm -f .cpu-train.tmp; \
	python -c 'import torch, transformers; print("[cpu-slim] Torch device available:", torch.device("cpu"))'; \
	du -sh .venv || true

guard-single-venv: ## Fail if more than one .venv/venv/env directory exists (enforce single environment)
	@COUNT=`find .. -maxdepth 4 -type d \( -name '.venv' -o -name 'venv' -o -name 'env' \) | wc -l`; \
	if [ "$$COUNT" -gt 1 ]; then echo "[guard] Multiple virtual environments detected:"; \
	  find .. -maxdepth 4 -type d \( -name '.venv' -o -name 'venv' -o -name 'env' \); \
	  echo "[guard] Please remove extras to maintain single-venv policy"; exit 1; \
	else echo "[guard] OK (single venv)"; fi

## ---- Quality ----
fmt: ## Run formatters
	. .venv/bin/activate && ruff check --fix . || true
	. .venv/bin/activate && isort .
	. .venv/bin/activate && black .

lint: ## Run linters
	. .venv/bin/activate && ruff check .
	. .venv/bin/activate && mypy . || true

check: lint test ## Lint + tests

## ---- Tests ----
pytest_args ?=
test: ## Run pytest
	. .venv/bin/activate && python -m pytest -q $(pytest_args)

## ---- Dev Server ----
serve: ## Run FastAPI dev server
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

chat-dev: ## Run API + dashboard dev (Vite)
	@if [ -f .api_pid ]; then OLD_PID=`cat .api_pid`; if ps -p $$OLD_PID >/dev/null 2>&1; then echo "Stopping previous API $$OLD_PID"; kill $$OLD_PID || true; fi; rm -f .api_pid; fi; \
	if ss -ltn | grep -q ':$$API_PORT '; then echo "Port $$API_PORT busy - freeing"; fuser -k $$API_PORT/tcp || true; fi; \
	(. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port $$API_PORT & echo $$! > .api_pid); \
	cd frontend/dashboard && npm run dev; \
	echo "Shutting down API dev server"; \
	if [ -f .api_pid ]; then kill `cat .api_pid` || true; rm .api_pid; fi

stop: ## Stop API dev server
	@if [ -f .api_pid ]; then kill `cat .api_pid` || true; rm .api_pid; echo "Stopped"; else echo "No running API"; fi

## ---- Containers ----
pg-up: ## Start disposable Postgres
	docker run -d --name zenglow-pg -e POSTGRES_USER=zenglow -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=zenglow -p 5432:5432 postgres:15-alpine >/dev/null 2>&1 || echo "Already running?"
	@echo "Postgres starting..."

pg-down: ## Remove disposable Postgres
	-docker rm -f zenglow-pg >/dev/null 2>&1 || true
	@echo "Postgres removed"

ollama-down: ## Remove ollama container
	-docker rm -f ollama >/dev/null 2>&1 || true
	@echo "Ollama removed (if existed)"

redis-down: ## Remove redis container
	-docker rm -f zenglow-redis >/dev/null 2>&1 || true
	@echo "Redis removed (if existed)"

stack-down: ## Remove all known containers
	-docker rm -f ollama zenglow-redis zenglow-pg zenglow-backend open-webui >/dev/null 2>&1 || true
	@echo "Stack containers removed"

compose-up: ## Bring up docker compose stack (build if needed)
	docker compose up -d
	docker compose ps

ollama-pull: ## Pull (ensure) default Ollama model in running container (MODEL=gemma:2b)
	@if ! docker ps --format '{{.Names}}' | grep -q '^ollama$$'; then echo "Ollama container not running (run: make compose-up or docker compose up -d ollama)"; exit 1; fi; \
	 MODEL=${MODEL:-gemma:2b}; echo "Ensuring model $$MODEL"; \
	 docker exec -e OLLAMA_ORIGINS='*' -e OLLAMA_MODELS=/root/.ollama -it ollama ollama pull $$MODEL || exit 1; \
	 echo "Model $$MODEL ready."

compose-restart: ## Full rebuild: down (wait) -> build -> up -> health check
	@echo "[compose] Stopping existing stack (ignore errors)"; \
	  docker compose down --remove-orphans || true; \
	  echo "[compose] Freeing common host ports (8000,11434,11435)"; \
	  fuser -k 8000/tcp 2>/dev/null || true; \
	  fuser -k 11434/tcp 2>/dev/null || true; \
	  fuser -k 11435/tcp 2>/dev/null || true; \
	  echo "[compose] Building images (pull latest bases)"; \
	  docker compose build --pull; \
	  echo "[compose] Starting services"; \
	  docker compose up -d; \
	  echo "[compose] Waiting for backend health endpoint (max 45s)"; \
	  timeout 45 bash -c 'until curl -sf localhost:8000/health >/dev/null 2>&1; do sleep 2; done' || echo "[compose] Backend health timed out"; \
	  docker compose ps

## ---- Builds ----
dashboard-build: ## Build full dashboard
	cd frontend/dashboard && npm run build
	mkdir -p app/static/dashboard && cp -r frontend/dashboard/dist/* app/static/dashboard/
	@echo "Dashboard synced"

dashboard-build-nometrics: ## Build dashboard without metrics polling
	cd frontend/dashboard && VITE_DISABLE_METRICS=1 npm run build
	mkdir -p app/static/dashboard && cp -r frontend/dashboard/dist/* app/static/dashboard/
	@echo "Dashboard (no metrics) synced"

chat-build: ## Build chat-only UI (metrics disabled)
	cd frontend/dashboard && VITE_DISABLE_METRICS=1 npm run build
	mkdir -p app/static/dashboard && cp -r frontend/dashboard/dist/* app/static/dashboard/
	@echo "Chat UI build complete"

embed-worker: ## Run async embedding worker locally (DATABASE_URL=... override EMBED_ENDPOINT=... BATCH_SIZE=32 POLL_INTERVAL=5)
	@if [ -z "${DATABASE_URL}" ]; then echo "Set DATABASE_URL env or pass --db-url"; fi; \
	. .venv/bin/activate && python scripts/async_embedding_worker.py ${DB_ARGS}

## ---- Utilities ----
clear-cache: ## Flush Redis DB (dangerous)
	. .venv/bin/activate && python -c 'import os,redis; r=redis.Redis(host=os.getenv("REDIS_HOST","localhost"),port=int(os.getenv("REDIS_PORT","6379")),db=int(os.getenv("REDIS_DB","0"))); r.flushdb(); print("Flushed")'

migrate: ## Apply pending SQL migrations (DRY_RUN=1 to preview)
	. .venv/bin/activate && python scripts/apply_migrations.py

ensure-phi3: ## Ensure phi3 model pulled to Ollama host
	bash scripts/ensure_phi3_model.sh

piper-voices: ## Download Piper voice models (amy, alan, southern male)
	bash scripts/ensure_piper_voices.sh

audio-setup: ## Setup whisper + piper voices (end-to-end STT/TTS assets)
	$(MAKE) whisper-setup
	$(MAKE) piper-voices

watch-profile: ## Watch a member profile for changes (FULL_NAME="Charles Bowen" INTERVAL=20)
	FULL_NAME=${FULL_NAME:-"Charles Bowen"}; \
	INTERVAL=${INTERVAL:-20}; \
	python scripts/profile_change_watcher.py --full-name "$$FULL_NAME" --interval $$INTERVAL ${DSN:+--dsn $$DSN} ${REDIS_URL:+--redis-url $$REDIS_URL}

whisper-setup: ## Setup whisper.cpp (build binary)
	bash scripts/setup_whisper_cpp.sh

print-env: ## Print key env vars
	@echo RAG_FUSION_LTR_WEIGHT=${RAG_FUSION_LTR_WEIGHT}
	@echo RAG_FUSION_CONCEPTUAL_WEIGHT=${RAG_FUSION_CONCEPTUAL_WEIGHT}
	@echo EMBED_ENDPOINT=${EMBED_ENDPOINT}

## ---- Governance / SOP ----
fact-scan: ## Scan dataset for embellishing phrases (PATH=dataset.jsonl)
	@if [ -z "${PATH}" ]; then echo "Provide PATH= path to jsonl"; exit 1; fi; \
	. .venv/bin/activate && python scripts/dataset_fact_check_scan.py --path ${PATH}
## ---- Datasets ----
manifest: ## Build consolidated processed dataset manifest
	python3 fine_tuning/training/scripts/build_dataset_manifest.py --pretty

family-dataset: ## Build consolidated family dataset (outputs datasets/family/*.jsonl + manifest.json)
	. .venv/bin/activate && python scripts/build_family_dataset.py --out datasets/family

family-dataset-scan: ## Build + run factual scan over family all.jsonl
	$(MAKE) family-dataset && $(MAKE) fact-scan PATH=datasets/family/all.jsonl

family-artifact-corpus: ## Export artifact corpus JSONL (VAL=0.1 for split) -> datasets/family/artifact_corpus.jsonl
	. .venv/bin/activate && python scripts/export_family_artifact_corpus.py ${VAL:+--val-ratio ${VAL}}

dedupe-%: ## Deduplicate a JSONL (usage: make dedupe-path=path/to/file.jsonl FIELDS="prompt response")
	@if [ -z "${dedupe_in}" ]; then echo "Provide dedupe_in=... (input .jsonl)"; exit 1; fi; \
	 if [ -z "${dedupe_out}" ]; then echo "Provide dedupe_out=... (output .jsonl)"; exit 1; fi; \
	 FARGS=""; if [ -n "${FIELDS}" ]; then FARGS="--fields ${FIELDS}"; fi; \
	 python3 fine_tuning/training/scripts/dedupe_jsonl.py --in ${dedupe_in} --out ${dedupe_out} $$FARGS

interrupt-gen: ## Regenerate interruption recovery datasets (seed overridable: SEED=42)
	python3 fine_tuning/training/scripts/generate_interruption_recovery_dataset.py --out-dir fine_tuning/datasets/processed/interruption_handling --seed ${SEED}

## ---- Fine-Tune (Phi3 General Jeeves) ----
finetune-phi3-general: ## Run general Phi3 (Jeeves base) LoRA fine-tune (DATASET=path override)
	@DATASET_PATH=${DATASET:-data/general/jeeves_general_dataset.jsonl}; \
	CONF=fine_tuning/training/configs/phi3_general_lora.yaml; \
	if [ ! -f $$DATASET_PATH ]; then echo "Dataset $$DATASET_PATH missing"; exit 1; fi; \
	python fine_tuning/training/scripts/finetune_phi3_general.py --config $$CONF --dataset $$DATASET_PATH || exit 1; \
	echo "[finetune] Completed general Phi3 LoRA training"

finetune-phi3-jarvis-mix: ## Fine-tune Phi3 on Jarvis mix flattened dataset (ensure jarvis-mix-phi3 run first)
	@DATASET_PATH=${DATASET:-fine_tuning/datasets/processed/jarvis_mix_phi3/jarvis_mix_phi3_flat.jsonl}; \
	CONF=fine_tuning/training/configs/phi3_jarvis_mix_lora.yaml; \
	if [ ! -f $$DATASET_PATH ]; then echo "Dataset $$DATASET_PATH missing (run make jarvis-mix-phi3)"; exit 1; fi; \
	python fine_tuning/training/scripts/finetune_phi3_general.py --config $$CONF --dataset $$DATASET_PATH || exit 1; \
	echo "[finetune] Completed Jarvis mix Phi3 LoRA training"

finetune-phi3-family: ## Fine-tune Phi3 on family dataset (QLORA=1 RUN_ID optional) builds dataset if missing
	@if [ ! -f datasets/family/all.jsonl ]; then echo "[family] Dataset missing -> building"; $(MAKE) family-dataset; fi; \
	. .venv/bin/activate && python scripts/finetune_phi3_family.py || exit 1; \
	echo "[family] Training complete (see runs/phi3_family_*)"

eval-phi3-family-latest: ## Run minimal eval on most recent family run (BASE overrides PHI3_MODEL)
	RUN_DIR=$$(ls -dt runs/phi3_family_* 2>/dev/null | head -n1); \
	if [ -z "$$RUN_DIR" ]; then echo "No family runs found"; exit 1; fi; \
	BASE=${BASE:-$$(python -c 'import os,sys;print(os.getenv("PHI3_MODEL","microsoft/Phi-3-mini-4k-instruct"))')}; \
	. .venv/bin/activate && python scripts/eval_phi3_family_minimal.py --run-dir $$RUN_DIR --base-model $$BASE; \
	echo "[eval] Wrote $$RUN_DIR/eval.json"

family-migrate: ## Apply family context + inference logging migration (requires psql access) (DSN=...) 
	@if [ -z "${DSN}" ]; then echo "Provide DSN= postgres connection string"; exit 1; fi; \
	FILE=sql/migrations/20250904_family_context_and_inference_logging.sql; \
	if [ ! -f $$FILE ]; then echo "Migration file $$FILE missing"; exit 1; fi; \
	psql "${DSN}" -v ON_ERROR_STOP=1 -f $$FILE && echo "[family-migrate] Applied $$FILE"

family-seed: ## Seed Postgres family tables from in-memory store (FAMILY_PG_DSN=...) 
	@if [ -z "${FAMILY_PG_DSN}" ]; then echo "Set FAMILY_PG_DSN env"; exit 1; fi; \
	. .venv/bin/activate && FAMILY_PG_DSN=${FAMILY_PG_DSN} python scripts/family_pg_seed.py

artifact-corpus-eval: ## Evaluate artifact corpus JSONL (CORPUS=datasets/family/artifact_corpus.jsonl)
	@if [ -z "${CORPUS}" ]; then echo "Provide CORPUS= path (artifact_corpus.jsonl)"; exit 1; fi; \
	. .venv/bin/activate && python scripts/eval_phi3_family_artifacts.py --corpus ${CORPUS}

jeeves-train-prep: ## Generate hybrid + RAG usage + audit + optional bundle (ARGS="--include-rag-batches --audit --bundle-tar artifacts/jeeves_bundle.tar.gz")
	python scripts/jeeves_training_runner.py $(ARGS)

jarvis-mix-phi3: ## Build Jarvis mix (v2) and flatten for Phi3 fine-tune
	python fine_tuning/training/jarvis_mix/build_jarvis_mix_v2.py \
	  --manifest fine_tuning/training/jarvis_mix/mix_manifest.example.json \
	  --out-dir fine_tuning/datasets/processed/jarvis_mix_phi3 --flatten

embed-finetune: ## Fine-tune embedding model (DATA=path OUTPUT=dir BASE=BAAI/bge-small-en-v1.5 EPOCHS=1 BATCH=64)
	@if [ -z "${DATA}" ]; then echo "Provide DATA= path to pairs file (tsv/csv/jsonl)"; exit 1; fi; \
	if [ -z "${OUTPUT}" ]; then echo "Provide OUTPUT= output directory"; exit 1; fi; \
	BASE=${BASE:-BAAI/bge-small-en-v1.5}; EPOCHS=${EPOCHS:-1}; BATCH=${BATCH:-64}; LR=${LR:-2e-5}; \
	. .venv/bin/activate && python fine_tuning/training/scripts/train_embedding_model.py \
	  --data ${DATA} --output ${OUTPUT} --base-model $$BASE --epochs $$EPOCHS --batch-size $$BATCH --lr $$LR ${USE_LORA:+--use-lora}

embed-quantize: ## Quantize embedding model (MODEL=dir OUTPUT=dir DTYPE=int8|int4)
	@if [ -z "${MODEL}" ]; then echo "Provide MODEL= path to trained model dir"; exit 1; fi; \
	if [ -z "${OUTPUT}" ]; then echo "Provide OUTPUT= target directory"; exit 1; fi; \
	DTYPE=${DTYPE:-int8}; \
	. .venv/bin/activate && python fine_tuning/training/scripts/quantize_embedding_model.py --model-path ${MODEL} --output ${OUTPUT} --dtype $$DTYPE

embed-serve: ## Serve embedding model (MODEL=dir PORT=8000 HOST=0.0.0.0)
	@if [ -z "${MODEL}" ]; then echo "Provide MODEL= path to model dir"; exit 1; fi; \
	PORT=${PORT:-8000}; HOST=${HOST:-0.0.0.0}; DEVICE=${DEVICE:-}; CONC=${CONCURRENCY:-4}; BATCH=${BATCH:-32}; NORMALIZE=${NORMALIZE:-0}; \
	. .venv/bin/activate && SERVE_MODEL=${MODEL} SERVE_PORT=$$PORT SERVE_HOST=$$HOST SERVE_DEVICE=$$DEVICE SERVE_CONCURRENCY=$$CONC SERVE_BATCH_SIZE=$$BATCH SERVE_NORMALIZE=$$NORMALIZE python scripts/serve_embedding_model.py

## ---- Gate Embed (BGE) ----
gate-embed-health: ## Probe in-gateway embedder
	. .venv/bin/activate && curl -sf localhost:8000/embed/health | jq . || true

gate-embed-test: ## Test /embed endpoint (TEXTS='["hello","world"]')
	TEXTS=${TEXTS:-'["hello world"]'}; . .venv/bin/activate && curl -s -X POST localhost:8000/embed -H 'Content-Type: application/json' -d '{"texts":'"$$TEXTS"'}' | jq '.dimension,.count' || true

embed-pairs-func: ## Build BGE pairs from function spec (SPEC=path OUTPUT=data/emb_train/function_pairs.jsonl)
	@if [ -z "${SPEC}" ]; then echo "Provide SPEC= path to functions.json or openapi.yaml"; exit 1; fi; \
	OUT=${OUTPUT:-data/emb_train/function_pairs.jsonl}; \
	. .venv/bin/activate && python scripts/bge_build_function_pairs.py --spec ${SPEC} --output $$OUT && echo "[pairs] -> $$OUT"

embed-train-func: ## Train BGE on function pairs (PAIRS=path OUTPUT=models/bge-func BASE=BAAI/bge-small-en-v1.5)
	@if [ -z "${PAIRS}" ]; then echo "Provide PAIRS= path to pairs jsonl"; exit 1; fi; \
	OUT=${OUTPUT:-models/bge-func}; BASE=${BASE:-BAAI/bge-small-en-v1.5}; EPOCHS=${EPOCHS:-1}; BATCH=${BATCH:-64}; LR=${LR:-2e-5}; \
	. .venv/bin/activate && python scripts/bge_train_domain.py --pairs ${PAIRS} --base-model $$BASE --epochs $$EPOCHS --batch-size $$BATCH --lr $$LR --output $$OUT && echo "[bge] saved -> $$OUT"

gate-embed-point: ## Point gateway embedder to trained model (MODEL=models/bge-func) and print env hints
	MODEL=${MODEL:-models/bge-func}; \
	echo "Export these before starting the API:"; \
	echo export EMBED_MODEL_PATH=$$MODEL; \
	echo export EMBED_NORMALIZE=1; \
	echo export EMBED_BATCH=32;

gen-safety-interventions: ## Generate safety_moderation_interventions dataset (N=200)
	NVAL=$${N:-200}; . .venv/bin/activate && python fine_tuning/datasets/generation/generate_safety_moderation_interventions.py --n $$NVAL

gen-refusal-boundary: ## Generate refusal_boundary_cases dataset (N=200)
	NVAL=$${N:-200}; . .venv/bin/activate && python fine_tuning/datasets/generation/generate_refusal_boundary_cases.py --n $$NVAL

jarvis-mix: ## Build Jarvis mix dataset from manifest (outputs processed/jarvis_mix_v1)
	python fine_tuning/training/scripts/build_jarvis_mix.py

spgi-sample: ## Stream and store a small SPGISpeech sample (COUNT=1000)
	@if [ ! -d .venv ]; then echo "Create venv first (make train-deps)"; exit 1; fi; \
	. .venv/bin/activate; \
	COUNT=$${COUNT:-1000}; \
	python scripts/spgispeech_sample_download.py --count $$COUNT --out-dir data/raw/spgispeech/sample --manifest data/finetune/asr/spgispeech_sample.jsonl --write-audio

merge-asr: ## Merge individual ASR manifests on-demand (MANIFESTS="a.jsonl,b.jsonl" OUTPUT=out.jsonl WEIGHTS="1.0,1.5")
	@if [ -z "${MANIFESTS}" ]; then echo "Provide MANIFESTS=comma_separated_paths"; exit 1; fi; \
	if [ -z "${OUTPUT}" ]; then echo "Provide OUTPUT=output_path.jsonl"; exit 1; fi; \
	IFS=',' read -r -a MLIST <<< "${MANIFESTS}"; \
	CMD="python scripts/merge_asr_manifests.py"; \
	for m in "$$${MLIST[@]}"; do CMD="$$CMD --manifest $$m"; done; \
	if [ -n "${WEIGHTS}" ]; then IFS=',' read -r -a WLIST <<< "${WEIGHTS}"; for w in "$$${WLIST[@]}"; do CMD="$$CMD --weight $$w"; done; fi; \
	CMD="$$CMD --output ${OUTPUT} --shuffle --seed $${SEED:-42} --drop-empty-text --normalize-weights"; \
	if [ -n "${MAX_SAMPLES}" ]; then CMD="$$CMD --max-total-samples ${MAX_SAMPLES}"; fi; \
	if [ -n "${MAX_HOURS}" ]; then CMD="$$CMD --max-total-hours ${MAX_HOURS}"; fi; \
	echo "[merge] $$CMD"; \
	. .venv/bin/activate && eval "$$CMD"

esc50: ## Prepare ESC-50 noise dataset (OUT=data/raw/esc50 MANIFEST=data/finetune/asr/esc50_noise_manifest.jsonl)
	@if [ ! -d .venv ]; then echo "Create venv (make asr-train-deps)"; exit 1; fi; \
	. .venv/bin/activate; \
	OUT=${OUT:-data/raw/esc50}; MAN=${MANIFEST:-data/finetune/asr/esc50_noise_manifest.jsonl}; NOISE=${NOISE_LIST:-data/finetune/asr/esc50_noise_paths.txt}; \
	python scripts/esc50_prepare.py --out-dir $$OUT --manifest $$MAN --noise-list $$NOISE --export-audio

augment-noise: ## Overlay ESC-50 noise onto speech (SPEECH=manifest NOISE=manifest OUT_MANIFEST=out.jsonl COUNT=1000 SNR=5:20)
	@if [ -z "${SPEECH}" ]; then echo "Provide SPEECH= path to clean speech manifest"; exit 1; fi; \
	if [ -z "${NOISE}" ]; then echo "Provide NOISE= path to noise manifest"; exit 1; fi; \
	OUT=${OUT_MANIFEST:-data/finetune/asr/augmented_noise.jsonl}; \
	COUNT=${COUNT:-1000}; SNR=${SNR:-5:20}; OUTDIR=${OUT_DIR:-data/augmented/noise_mix}; \
	. .venv/bin/activate; \
	python scripts/augment_noise_overlay.py --speech-manifest ${SPEECH} --noise-manifest ${NOISE} --out-dir $$OUTDIR --out-manifest $$OUT --count $$COUNT --snr-db $$SNR --overwrite

dailytalk-sample: ## Sample English DailyTalk dialogs (COUNT=1000 OUTPUT=path VAL=0.05)
	@if [ ! -d .venv ]; then echo "Create venv (make asr-train-deps)"; exit 1; fi; \
	. .venv/bin/activate; \
	COUNT=${COUNT:-1000}; OUTPUT=${OUTPUT:-data/finetune/asr/dailytalk_en_sample.jsonl}; VAL=${VAL:-0.05}; \
	python scripts/dailytalk_sample_prepare.py --count $$COUNT --output $$OUTPUT --val-percent $$VAL

backfill-transcripts: ## Fill missing transcript text (IN=manifest OUT=out.jsonl MODEL=small.en LIMIT= optional)
	@if [ -z "${IN}" ]; then echo "Provide IN= input manifest"; exit 1; fi; \
	OUT=${OUT:-data/finetune/asr/backfilled.jsonl}; MODEL=${MODEL:-small.en}; LIMIT=${LIMIT:-}; \
	. .venv/bin/activate; \
	CMD="python scripts/backfill_transcripts.py --input ${IN} --output $$OUT --model $$MODEL --overwrite-output"; \
	if [ -n "$$LIMIT" ]; then CMD="$$CMD --limit $$LIMIT"; fi; \
	echo "[backfill] $$CMD"; eval "$$CMD"

libri-manifest: ## Build LibriSpeech manifest (ROOT=path OUTPUT=path)
	@if [ -z "${ROOT}" ]; then echo "Provide ROOT= path to Libri subset (e.g., data/raw/libri/LibriSpeech/train-clean-100)"; exit 1; fi; \
	OUT=${OUTPUT:-data/finetune/asr/libri_clean_manifest.jsonl}; \
	. .venv/bin/activate; \
	python scripts/librispeech_build_manifest.py --root ${ROOT} --output $$OUT

asr-audit: ## Audit ASR manifests for missing transcripts & duplicates
	@if ! ls data/finetune/asr/*manifest*.jsonl >/dev/null 2>&1; then echo "No manifest files found (pattern *manifest*.jsonl)"; exit 1; fi; \
	. .venv/bin/activate; \
	python scripts/asr_manifest_audit.py \
	  --manifests $$(ls data/finetune/asr/*manifest*.jsonl) \
	  --hash-mode quick \
	  --output-clean data/finetune/asr/audit_clean_unique.jsonl \
	  --output-missing data/finetune/asr/audit_missing.jsonl \
	  --output-dupes data/finetune/asr/audit_duplicates.jsonl \
	  --stats data/finetune/asr/audit_stats.json || true; \
	echo "[audit] Outputs:"; ls -lh data/finetune/asr/audit_*.jsonl 2>/dev/null || true; \
	echo "[audit] Stats:"; cat data/finetune/asr/audit_stats.json 2>/dev/null || true; \
	echo "[audit] Next: make backfill-transcripts IN=data/finetune/asr/audit_missing.jsonl OUT=..."

asr-lint: ## Lint transcripts in a manifest (MANIFEST=path OUT=prefix)
	@if [ -z "${MANIFEST}" ]; then echo "Provide MANIFEST= path to manifest"; exit 1; fi; \
	OUT=${OUT:-data/finetune/asr/lint_result}; \
	. .venv/bin/activate; \
	python scripts/asr_transcript_lint.py --manifest ${MANIFEST} \
	  --issues-jsonl $$OUT.issues.jsonl \
	  --report-json $$OUT.report.json \
	  --clean-jsonl $$OUT.cleaned.jsonl || true; \
	echo "[lint] Outputs:"; ls -lh $$OUT.* 2>/dev/null || true

asr-tag: ## Add prompt/tags to a manifest (IN=manifest OUT=output.jsonl STYLE=plain|instruct|minimal)
	@if [ -z "${IN}" ]; then echo "Provide IN= path to manifest"; exit 1; fi; \
	if [ -z "${OUT}" ]; then echo "Provide OUT= output path"; exit 1; fi; \
	STYLE=${STYLE:-plain}; \
	. .venv/bin/activate; \
	python scripts/asr_add_prompt_tags.py --input ${IN} --output ${OUT} --prompt-style $$STYLE; \
	echo "[tag] Wrote tagged manifest to ${OUT}"

balanced-asr-thirds: ## Full pipeline: build/sample three manifests equally (COUNT=300 LIBRI_ROOT=path) -> merged + tagged
	@if [ ! -d .venv ]; then echo "Create env (make asr-train-deps)"; exit 1; fi; \
	. .venv/bin/activate; \
	COUNT=${COUNT:-300}; \
	LIBRI_ROOT=${LIBRI_ROOT:-data/raw/libri/LibriSpeech/train-clean-100}; \
	if [ ! -d "$$LIBRI_ROOT" ]; then echo "Libri root $$LIBRI_ROOT missing"; exit 1; fi; \
	echo "[thirds] 1/7 DailyTalk sample"; make dailytalk-sample COUNT=$$COUNT OUTPUT=data/finetune/asr/dailytalk_en_sample.jsonl; \
	echo "[thirds] 2/7 SPGI sample"; make spgi-sample COUNT=$$COUNT; \
	echo "[thirds] 3/7 Libri manifest build"; make libri-manifest ROOT=$$LIBRI_ROOT OUTPUT=data/finetune/asr/libri_full_manifest.jsonl; \
	echo "[thirds] 4/7 Libri sampling"; python scripts/asr_sample_manifest.py --input data/finetune/asr/libri_full_manifest.jsonl --output data/finetune/asr/libri_sample_manifest.jsonl --count $$COUNT --seed 42; \
	echo "[thirds] 5/7 Tagging"; \
	python scripts/asr_add_prompt_tags.py --input data/finetune/asr/dailytalk_en_sample.jsonl --output data/finetune/asr/dailytalk_en_sample.tagged.jsonl --prompt-style instruct; \
	python scripts/asr_add_prompt_tags.py --input data/finetune/asr/spgispeech_sample.jsonl --output data/finetune/asr/spgispeech_sample.tagged.jsonl --prompt-style instruct; \
	python scripts/asr_add_prompt_tags.py --input data/finetune/asr/libri_sample_manifest.jsonl --output data/finetune/asr/libri_sample_manifest.tagged.jsonl --prompt-style instruct; \
	echo "[thirds] 6/7 Merge exact thirds"; \
	python scripts/merge_asr_manifests.py \
	  --manifest data/finetune/asr/dailytalk_en_sample.tagged.jsonl \
	  --manifest data/finetune/asr/spgispeech_sample.tagged.jsonl \
	  --manifest data/finetune/asr/libri_sample_manifest.tagged.jsonl \
	  --output data/finetune/asr/merged_thirds.jsonl \
	  --exact-proportions --target-total-samples $$((COUNT*3)) --normalize-weights --drop-empty-text --shuffle --seed 42; \
	echo "[thirds] 7/7 Lint merged"; \
	python scripts/asr_transcript_lint.py --manifest data/finetune/asr/merged_thirds.jsonl --issues-jsonl data/finetune/asr/merged_thirds.lint.issues.jsonl --report-json data/finetune/asr/merged_thirds.lint.report.json --clean-jsonl data/finetune/asr/merged_thirds.cleaned.jsonl --style-restrict --style-normalize; \
	echo "[thirds] Done. Outputs in data/finetune/asr/ (merged_thirds*)"

asr-pipeline: ## Run orchestrated ASR pipeline (COUNT=300 LIBRI_ROOT=path) -> final tagged thirds
	@if [ ! -d .venv ]; then echo "Create env (make asr-train-deps)"; exit 1; fi; \
	. .venv/bin/activate; \
	python fine_tuning/training/scripts/asr/run_asr_pipeline.py --count ${COUNT:-300} --libri-root ${LIBRI_ROOT:-data/raw/libri/LibriSpeech/train-clean-100} --seed ${SEED:-42}

whisper-tag-dataset: ## Build tagged whisper dataset (IN=manifest OUT=tagged.jsonl)
	@if [ -z "${IN}" ]; then echo "Need IN= input manifest"; exit 1; fi; \
	OUT=${OUT:-data/whisper_finetune/tagged_dataset.jsonl}; \
	. .venv/bin/activate; \
	python fine_tuning/training/scripts/asr/whisper_build_tagged_dataset.py --input ${IN} --output $$OUT; \
	echo "[tag-dataset] Wrote $$OUT"

whisper-tag-stats: ## Compute tag distribution & entropy (IN=tagged.jsonl OUTDIR=stats/)
	@if [ -z "${IN}" ]; then echo "Need IN= tagged dataset"; exit 1; fi; \
	OUTDIR=${OUTDIR:-data/whisper_finetune/stats}; \
	. .venv/bin/activate; \
	python fine_tuning/training/scripts/asr/whisper_tag_stats.py --input ${IN} --out-dir $$OUTDIR

asr-wrapper-parity-check: ## Ensure ASR wrapper scripts exist for core top-level ASR scripts (fails if missing)
	@python - <<'EOF'
	import sys, pathlib
	root=pathlib.Path('.').resolve()
	core=['asr_manifest_audit.py','asr_transcript_lint.py','asr_add_prompt_tags.py','merge_asr_manifests.py','asr_sample_manifest.py','backfill_transcripts.py','augment_noise_overlay.py','librispeech_build_manifest.py','spgispeech_sample_download.py','dailytalk_sample_prepare.py','esc50_prepare.py']
	wrap_dir=root/'fine_tuning'/'training'/'scripts'/'asr'
	missing=[]
	for c in core:
	    stem=c.replace('.py','')
	    wrapper=wrap_dir/f'wrapper_{stem}.py'
	    if not wrapper.exists():
	        missing.append(str(wrapper))
	if missing:
	    print('[PARITY] Missing wrappers:')
	    for m in missing: print(' -', m)
	    sys.exit(1)
	print('[PARITY] All wrappers present')
	EOF

infer-phi35-lora: ## Run inference with Phi-3.5 base + LoRA adapter (BASE=..., ADAPTER=..., PROMPT="...")
	@if [ -z "${ADAPTER}" ]; then echo "Provide ADAPTER= path to LoRA adapter dir"; exit 1; fi; \
	 if [ -z "${PROMPT}" ]; then echo "Provide PROMPT= prompt string"; exit 1; fi; \
	 BASE=${BASE:-microsoft/Phi-3.5-mini-instruct}; \
	 . .venv/bin/activate 2>/dev/null || true; \
	 python3 scripts/infer_phi35_lora.py --base $$BASE --adapter ${ADAPTER} --prompt "${PROMPT}" | tail -n +1

aos-predict-win: ## Train/eval AoS win predictor (DSN=... PLAYER=optional SCHEMA=optional)
	@if [ -z "${DSN}" ]; then echo "Provide DSN= postgres connection string"; exit 1; fi; \
	 python3 scripts/aos_predict_win.py --dsn "${DSN}" ${PLAYER:+--player "${PLAYER}"} ${SCHEMA:+--schema "${SCHEMA}"} ${WINDOW:+--window ${WINDOW}}

chrono-train: ## Train simple time-series regressor for health metric (DSN=... METRIC=... PERSON=optional SCHEMA=optional)
	@if [ -z "${DSN}" ]; then echo "Provide DSN= postgres connection string"; exit 1; fi; \
	 if [ -z "${METRIC}" ]; then echo "Provide METRIC= metric name"; exit 1; fi; \
	 python3 scripts/chronos_train.py --dsn "${DSN}" --metric "${METRIC}" ${PERSON:+--person-id "${PERSON}"} ${SCHEMA:+--schema "${SCHEMA}"}

pgvector-rerank: ## ANN recall via pgvector then CrossEncoder rerank (DSN=... QUERY=... SCHEMA=optional)
	@if [ -z "${DSN}" ]; then echo "Provide DSN= postgres connection string"; exit 1; fi; \
	 if [ -z "${QUERY}" ]; then echo "Provide QUERY= search text"; exit 1; fi; \
	 python3 scripts/pgvector_rerank.py --dsn "${DSN}" --query "${QUERY}" ${SCHEMA:+--schema "${SCHEMA}"} ${TOPK:+--topk ${TOPK}} ${RERANKER:+--reranker "${RERANKER}"} ${EMBED_DIM:+--embed-dim ${EMBED_DIM}}

swarm-sim: ## Simulate star-ring + mesh explorer swarm routing (POLICY=configs/swarm_policy.yaml STEPS=1000)
	POL=${POLICY:-configs/swarm_policy.yaml}; STEPS=${STEPS:-1000}; \
	 python3 scripts/swarm_scheduler.py --policy $$POL --steps $$STEPS

.PHONY: help venv setup freeze deps-gpu-or-cpu fmt lint check test serve chat-dev stop pg-up pg-down ollama-down redis-down stack-down compose-up compose-restart dashboard-build dashboard-build-nometrics chat-build clear-cache whisper-setup print-env sop-sync manifest dedupe-% interrupt-gen pg-enable-extensions pg-apply-prediction-schema pg-embed-index pg-aos-stats pg-apply-prediction-schema-pii pg-embed-index-pii
