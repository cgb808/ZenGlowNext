package ingester

import (
    "errors"
    "io"
    "log"

    "google.golang.org/grpc"
)

// We implement registration in a separate function that main calls.
// This file attempts to import the generated package; if missing, we fall back
// to a no-op registration and return an error, allowing the program to build
// before running protoc.

// registerIngestion registers the gRPC ingestion service implementation.
func Register(s *grpc.Server) error {
    // Use build tag trick? Keep it simple: try to reference the package name via type assertion.
    // We'll define an inner impl in a separate file that only compiles once the generated code exists.
    return errors.New("ingestion stubs not generated (run protoc)" )
}

// Below is the actual service impl (in another file) once codegen exists.
// The code-generated interface looks like:
// type IngestionServiceServer interface {
//     IngestStream(IngestionService_IngestStreamServer) error
// }
// Our implementation will count records and log basic stats.

// helper used by real impl
func drainStream[T any](recv func() (T, error)) (int, error) {
    n := 0
    for {
        _, err := recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return n, err
        }
        n++
    }
    log.Printf("ingested %d records", n)
    return n, nil
}
