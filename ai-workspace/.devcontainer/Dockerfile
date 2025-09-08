# AI Training Devcontainer
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Optional ARGs
ARG INSTALL_NODE="20"
ARG POETRY_VERSION="1.8.3"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    NVM_DIR=/usr/local/share/nvm

# Core OS + tooling (CUDA not included - CPU training / light fine-tunes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential wget curl ca-certificates \
    libjpeg-dev zlib1g-dev libpq-dev pkg-config \
    openssh-client gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node (for ancillary scripts) & Poetry
RUN if [ "$INSTALL_NODE" != "none" ]; then \
      su vscode -c ". /usr/local/share/nvm/nvm.sh && nvm install $INSTALL_NODE && nvm alias default $INSTALL_NODE"; \
    fi && \
    pip install --no-cache-dir poetry==${POETRY_VERSION}

# Copy requirements early for layer caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true

# Workspace root is volume mounted; no source COPY

# Helpful default tools
RUN pip install --no-cache-dir jupyterlab notebook ipykernel black isort pre-commit

# Create a default Python kernel name
RUN python -m ipykernel install --user --name zenglow-ai --display-name "ZenGlow AI"

CMD ["sleep", "infinity"]
