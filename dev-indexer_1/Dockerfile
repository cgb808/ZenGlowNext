############################################################
# Multi-stage Indexer Image                                #
# Stage 1: builder (deps, wheels)                          #
# Stage 2: runtime (slim, no build toolchain)              #
# Targets:
#   - prod (default): minimal runtime, non-root            #
#   - dev: adds git/sudo and enables reload                #
############################################################

ARG PYTHON_VERSION=3.12
ARG ENABLE_WHISPER=0          # set to 1 to build & include whisper.cpp + model
ARG WHISPER_MODEL=small.en    # whisper.cpp model to fetch when enabled
ARG INSTALL_HEAVY_EXTRAS=0    # set to 1 to install heavy optional deps (torch/transformers)
FROM python:${PYTHON_VERSION}-slim AS builder

ARG UID=1000
ARG GID=1000
ARG USERNAME=cgb808
ENV DEBIAN_FRONTEND=noninteractive \
	PIP_NO_CACHE_DIR=1 \
	PYTHONUNBUFFERED=1 \
	APP_HOME=/workspace
WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential curl ca-certificates git \
	&& rm -rf /var/lib/apt/lists/*

# Requirements caching
COPY requirements.txt ./
# Include referenced nested requirements file (root file uses -r infrastructure/configs/requirements.txt)
COPY infrastructure/configs/requirements.txt infrastructure/configs/requirements.txt
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# Copy source (minimal needed for potential editable installs later)
COPY app ./app
COPY start.sh /tmp/start.sh
COPY scripts/fetch_whisper_cpp.sh /tmp/fetch_whisper_cpp.sh

# Optional: build whisper.cpp + selected model (guarded by ENABLE_WHISPER to avoid large default image)
RUN mkdir -p vendor/whisper.cpp \
		&& if [ "${ENABLE_WHISPER}" = "1" ]; then \
				 chmod +x /tmp/fetch_whisper_cpp.sh && MODEL=${WHISPER_MODEL} /tmp/fetch_whisper_cpp.sh ; \
			 else \
				 echo "[whisper] skipped (ENABLE_WHISPER!=1)" ; \
			 fi

# Optional: build wheels for heavy extras only when explicitly requested
RUN if [ "${INSTALL_HEAVY_EXTRAS}" = "1" ]; then \
		pip wheel --wheel-dir /wheels transformers torch sentence-transformers whispercpp stt ; \
	else \
		echo "[extras] skipped heavy extras wheel build" ; \
	fi

############################################################
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG UID=1000
ARG GID=1000
ARG USERNAME=cgb808
ARG ENABLE_WHISPER=0
ARG WHISPER_MODEL=small.en
ARG INSTALL_HEAVY_EXTRAS=0
ENV PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	APP_HOME=/workspace \
	DEBIAN_FRONTEND=noninteractive
WORKDIR ${APP_HOME}

# Minimal runtime deps; extend if audio/native libs required later
RUN apt-get update && apt-get install -y --no-install-recommends \
	ca-certificates curl procps \
	&& groupadd -g ${GID} ${USERNAME} \
	&& useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME} \
	&& rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy app code last for cache efficiency
COPY app ./app
COPY start.sh /usr/local/bin/start.sh

# Copy whisper.cpp assets if built (directory will exist only when ENABLE_WHISPER=1)
COPY --from=builder /workspace/vendor/whisper.cpp /opt/whisper.cpp

RUN chmod +x /usr/local/bin/start.sh \
	&& chown -R ${USERNAME}:${USERNAME} ${APP_HOME} \
	&& if [ "${ENABLE_WHISPER}" != "1" ]; then rm -rf /opt/whisper.cpp 2>/dev/null || true; fi

USER ${USERNAME}
EXPOSE 8000
ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 ENABLE_RELOAD=0 \
	WHISPER_CPP_DIR=/opt/whisper.cpp WHISPER_MODEL=${WHISPER_MODEL}

ENTRYPOINT ["/usr/local/bin/start.sh"]
# Default command suitable for production (no reload). Dev target overrides via ENV.
CMD ["bash", "-lc", "exec uvicorn app.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT}"]

# ---------- Targets ----------
# Production target (default)
FROM runtime AS prod

# Development target: add git/sudo and enable reload by default
FROM runtime AS dev
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git sudo \
	&& usermod -aG sudo ${USERNAME} \
	&& echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-${USERNAME} \
	&& rm -rf /var/lib/apt/lists/*
USER ${USERNAME}
ENV ENABLE_RELOAD=1
CMD ["bash", "-lc", "exec uvicorn app.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} --reload"]
