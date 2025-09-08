# ZenGlow AI Training Workspace

Isolated environment for ML experimentation, fine-tuning, and data preparation. Keeps heavyweight deps and transient artifacts out of the main app devcontainer.

## Contents
- `.devcontainer/` dedicated VS Code remote container definition
- `requirements.txt` base Python stack (extend as needed)
- `docker-compose.ai.yml` orchestrates the training container + isolated Postgres
- `modules/` AI/ML modules and implementations
  - `personalization/` Chronotype detection and personalization features
- (optional) `.env` for experiment secrets / DSN (never commit secrets)

## Quick Start
```bash
# Build and start training environment
docker compose -f docker-compose.ai.yml up -d --build

# Attach VS Code: Command Palette > Dev Containers: Open Folder in Container...
#   Select ai-workspace (service: ai-train)

# (Inside container) install any added libs
pip install -r requirements.txt

# Launch Jupyter
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token='' --NotebookApp.password=''
```

Open http://localhost:8888 in browser.

## Database (Supabase Postgres Minimal)
- Host: localhost
- Port: 54324
- DB: ai_lab
- User: ai_lab / examplepassword

Use for lightweight experiment metadata, not production data.

## Conventions
- Place notebooks under `ai-workspace/notebooks/`
- Place raw scratch datasets under `ai-workspace/data/` (gitignored)
- Export model artifacts to `ai-workspace/models/` (gitignored except README)
- Keep only small derived samples (<5MB) in git if needed for tests

## Git Hygiene
Add to `.gitignore` (if not already):
```
ai-workspace/data/
ai-workspace/models/
ai-workspace/notebooks/.ipynb_checkpoints/
```

## Extending Stack
Add libs: append to `requirements.txt`, rebuild container or run `pip install -r requirements.txt` inside.
For GPU work later: replace base image with a CUDA-enabled devcontainer image + add `--gpus` flag when bringing up compose.

## Supabase Expansion (Optional)
If you need Auth/Rest/Realtime for simulation, you can copy the corresponding services from main `docker-compose.yml` and prefix with `ai-` (or reuse the existing stack if port collisions are acceptable).

## Cleanup
Stop containers:
```bash
docker compose -f docker-compose.ai.yml down
```
Remove dangling images/volumes occasionally:
```bash
docker system prune -f
```

## Security
Never commit actual secrets or large proprietary datasets. Use environment variables or external secure storage.
