# Ingestion gRPC Service

Contract: `services/ingestion/v1/ingestion.proto`

## Codegen (Go)

Requires protoc, protoc-gen-go, protoc-gen-go-grpc.

```bash
# Install tools (optional)
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate
make gen
```

## Run

```bash
go run -tags ingester_gen ./cmd/ingester # listens on :50051 (override with -addr)
```

## Next
- Implement embedding client and postgres batch insert (pgx copy).
- Add dedupe by content hash.
- Add health and metrics endpoints.

## Related
- Router contract: `services/router/v1/router.proto`
- Architecture overview: `docs/ARCHITECTURE_OVERVIEW.md`