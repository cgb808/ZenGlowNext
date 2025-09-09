# Log Service (Go) — Skeleton

This is a minimal scaffold for the centralized gRPC logging service described in `docs/logging-service.md`.

- Proto: `protos/services/logging/v1/logging.proto`
- Go module: `grpc/logservice`
- Entry: `grpc/logservice/main.go`
- Server: `grpc/logservice/internal/server/server.go`

Generate / Update stubs (example):

```bash
# from repo root, assuming `protoc` and `protoc-gen-go` / `protoc-gen-go-grpc` are installed
protoc -I protos \
  --go_out=protos --go_opt=paths=source_relative \
  --go-grpc_out=protos --go-grpc_opt=paths=source_relative \
  protos/services/logging/v1/logging.proto
```

Run the server:

```bash
cd grpc/logservice
go run ./...
```

Next steps:
- Implement file opening, rotation, compression in `sessionFileWriter`.
- Add env-config (LOG_DIR, LOG_MAX_SIZE_BYTES, etc.).
- Optional Redis notifications.
- Add a small Python client helper to stream frames from agents.
