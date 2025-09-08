## Devcontainer unified base: Python 3.12, Node 20, Java 17
# (Assumes the 0-3.12 tag exists; if not, adjust to the closest 1-* variant.)
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

ARG INSTALL_NODE="20"
ENV NVM_DIR=/usr/local/share/nvm

# Install Node 20 (under vscode user) & Java 17 + Postgres client & common build deps for ML libs
RUN if [ "${INSTALL_NODE}" != "none" ]; then \
        su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${INSTALL_NODE} && nvm alias default ${INSTALL_NODE}"; \
    fi \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        openjdk-17-jdk \
        postgresql-client \
        git \
        build-essential \
        wget curl \
        libxml2-dev libxslt1-dev \
        libjpeg-dev zlib1g-dev \
        pkg-config \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Pre-install heavy Python deps to bake them into the image layer (reduces re-install churn)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true

# Note: project source is volume-mounted by docker-compose; no COPY of app code here.

## Show versions (helpful during build logs)
RUN echo "Python: $(python -V)" && \
    su vscode -c ". /usr/local/share/nvm/nvm.sh && node -v && npm -v" && \
    java -version