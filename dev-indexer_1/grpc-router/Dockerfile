# syntax=docker/dockerfile:1

ARG GO_VERSION=1.23

FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /src

# Install build deps
RUN apk add --no-cache git make protoc

# Copy go module files first for better caching
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the source
COPY . .

# Generate protobuf stubs if Makefile exists
RUN make Gen-go || true

# Build the router binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/router ./cmd/router

FROM alpine:3.19 AS runtime
WORKDIR /app

# Install netcat for health/wait
RUN apk add --no-cache netcat-openbsd ca-certificates

ENV ADDR=":50052"

COPY --from=builder /out/router /app/router

# Simple entrypoint with wait-for-redis trigger
RUN printf '#!/bin/sh\nset -e\n: "${REDIS_HOST:=redis}"\n: "${REDIS_PORT:=6379}"\necho "[router] waiting for redis at ${REDIS_HOST}:${REDIS_PORT}"\nfor i in $(seq 1 60); do\n  if nc -z "$REDIS_HOST" "$REDIS_PORT"; then\n    echo "[router] redis is up"; break;\n  fi;\n  sleep 2;\ndone\nexec /app/router -addr "$ADDR" "$@"\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 50052

HEALTHCHECK --interval=10s --timeout=3s --retries=10 --start-period=10s \
  CMD nc -z 127.0.0.1 50052 || exit 1

ENTRYPOINT ["/bin/sh","/app/entrypoint.sh"]
