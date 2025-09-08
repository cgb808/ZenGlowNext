# AI Agents Workspace

This directory houses all AI / ML related components:

- `zendexer/` ingestion, RAG, and wearable data pipelines
- `fastapi-gateway/` lightweight API gateway / model serving access
- `EXPORT ADAPTERS/` health platform export adapters
- `llama.cpp/` upstream inference tooling (treated mostly as vendor code)
- `agents/` packaged model weights / fine-tuned variants (ignored for large blobs)
- `physionet.org/` reference datasets metadata or fetch scripts (not raw large datasets)
- `transmission-pipeline/` streaming / bridge scripts
- Wearables training assets under `zendexer/wearables/`

## Tracking Policy

Keep in git:
* Source code (Python / TS / config YAML / JSON metadata) < 1MB each
* Lightweight README / docs / small schemas
* Minimal placeholder files (e.g. `.gitkeep`, model README)

Do NOT commit:
* Virtual environments (`venv/`, `analysis_env/`, `venv_zenglow/`)
* Large model weights (`*.gguf`, `*.tflite`, `*.h5`, `*.pkl`, `*.pb`)
* Generated vector indexes (`vector-store/` content) & embeddings
* Raw large datasets or archives (`*.tar.gz`, large `.csv` > ~5MB) – store externally
* Checkpoints / saved_model directories

## Manual Update Workflow

1. Run `scripts/branch_diff.sh` (optional) to see branch impact.
2. Stage only code & metadata: `git add -p ai-agents/...` (avoid bulk `git add ai-agents`).
3. Verify large files are ignored: `git check-ignore path/to/file` before committing.
4. Commit with conventional message: `feat(ai-agents): ...`, `chore(ai-agents): ...`, etc.
5. For model retrains, record parameters & dataset hash in a small JSON or YAML (do **not** add the model blob) under `ai-agents/agents/metadata/` (create if absent).
6. If you must share a weight, prefer an object store (S3 / Supabase storage) and document the retrieval command in this README.

### Sync Helper

You can snapshot ignored large artifacts to an adjacent cache so they survive cleans / reclones. Provided script:

```
./ai-agents/sync-ai-agents.sh backup   # rsync eligible (non-blocked) artifacts to ../ai-agents-cache
./ai-agents/sync-ai-agents.sh restore  # restore from cache into working tree
```

Adjust exclusion patterns inside the script as needs evolve.

## Syncing External Assets

Use the helper script below to rsync selected local large artifacts to a non-tracked mirror (e.g. `../ai-agents-cache`). This keeps the working copy clean.

```
./ai-agents/sync-ai-agents.sh backup   # push large ignored stuff to cache
./ai-agents/sync-ai-agents.sh restore  # pull back from cache
```

## Regenerating Vector Index

1. Ensure environment: `python -m venv venv_zenglow && source venv_zenglow/bin/activate && pip install -r zendexer/requirements.txt`
2. Run data prep: `python zendexer/wearables/run_complete_pipeline.py --mode prep`
3. Build embeddings: `python zendexer/agent_dev.py --build-index` (adjust flags)
4. Resulting index files appear under `zendexer/vector-store/` (ignored by git).

## Model Documentation Stub

Add a `models/README.md` inside relevant subdirectories describing:
* Model name & version
* Training dataset reference / hash
* Hyperparameters summary
* Evaluation metrics (accuracy / F1 / etc.)
* Export formats produced (.tflite, .gguf, etc.)

## Enforcement Tips

Pre-commit (optional): add a hook rejecting >10MB non-ignored files:
```
#!/usr/bin/env bash
set -e
git diff --cached --name-only | while read f; do
  [ -f "$f" ] || continue
  sz=$(stat -c%s "$f")
  if [ $sz -gt 10000000 ]; then
    echo "Blocked large file: $f ($sz bytes)." >&2
    exit 1
  fi
done
```
Place in `.git/hooks/pre-commit` (not versioned) and `chmod +x` it.

### Pre-Commit Guard (Extended Sample)

For more nuanced blocking (size + specific model patterns) use the maintained sample at `scripts/pre-commit.sample`:

```
cp scripts/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Then tune `MAX_SIZE_MB` and `BLOCK_PATTERNS` in that file.

## Future Improvements
* Scripted dataset hashing & metadata registry
* Automatic upload of new weights to remote storage with signed URLs
* CI guard: fail if disallowed patterns appear in diff

---
Maintain lean repository; treat this directory as code + metadata only.
