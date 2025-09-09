# syntax=docker/dockerfile:1

ARG GO_VERSION=1.23

FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git make protoc

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN make gen-go || true

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/logservice ./cmd/logservice

FROM alpine:3.19 AS runtime
WORKDIR /app

RUN apk add --no-cache netcat-openbsd ca-certificates

ENV ADDR=":50051"

COPY --from=builder /out/logservice /app/logservice

RUN printf '#!/bin/sh\nset -e\n: "${POSTGRES_HOST:=db}"\n: "${POSTGRES_PORT:=5432}"\necho "[logservice] waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}"\nfor i in $(seq 1 60); do\n  if nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; then\n    echo "[logservice] postgres is up"; break;\n  fi;\n  sleep 2;\ndone\nexec /app/logservice -addr "$ADDR" "$@"\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 50051

HEALTHCHECK --interval=10s --timeout=3s --retries=10 --start-period=10s \
  CMD nc -z 127.0.0.1 50051 || exit 1

ENTRYPOINT ["/bin/sh","/app/entrypoint.sh"]
