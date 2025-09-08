############################################################
# Multi-stage Indexer Image                                #
# Stage 1: builder (deps, wheels)                          #
# Stage 2: runtime (slim, no build toolchain)              #
# Optional dev image via DEV_IMAGE=1 adds git, sudo, etc.  #
############################################################

ARG PYTHON_VERSION=3.12
ARG ENABLE_WHISPER=0          # set to 1 to build & include whisper.cpp + model
ARG WHISPER_MODEL=small.en    # whisper.cpp model to fetch when enabled
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

# Install additional dependencies for new services
RUN pip install --no-cache-dir transformers torch sentence-transformers
RUN pip install --no-cache-dir whispercpp
RUN pip install --no-cache-dir stt

############################################################
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG UID=1000
ARG GID=1000
ARG USERNAME=cgb808
ARG DEV_IMAGE=0
ARG ENABLE_WHISPER=0
ARG WHISPER_MODEL=small.en
ENV PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	APP_HOME=/workspace \
	DEBIAN_FRONTEND=noninteractive
WORKDIR ${APP_HOME}

# Minimal runtime deps; extend if audio/native libs required later
RUN apt-get update && apt-get install -y --no-install-recommends \
	ca-certificates curl procps \
	$( [ "${DEV_IMAGE}" = "1" ] && echo "git sudo" ) \
	&& groupadd -g ${GID} ${USERNAME} \
	&& useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME} \
	&& if [ "${DEV_IMAGE}" = "1" ]; then usermod -aG sudo ${USERNAME} && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-${USERNAME}; fi \
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
# Reload only for dev image (override at runtime: -e ENABLE_RELOAD=1)
CMD ["bash", "-lc", "exec uvicorn app.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} $( [ \"$ENABLE_RELOAD\" = \"1\" ] && echo '--reload' )" ]
