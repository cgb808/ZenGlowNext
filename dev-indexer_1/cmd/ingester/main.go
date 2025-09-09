package main

import (
    "context"
    "flag"
    "log"
    "net"
    "os"
    "os/signal"
    "syscall"

    "google.golang.org/grpc"
    "google.golang.org/grpc/health"
    healthpb "google.golang.org/grpc/health/grpc_health_v1"

    ingester "github.com/cgb808/ZenGlowNext/dev-indexer_1/internal/ingester"
)

// Import the generated ingestion service after codegen.
// go:generate comments handled via Makefile/protoc in README.

func main() {
    addr := flag.String("addr", getEnv("INGEST_ADDR", ":50051"), "listen address")
    flag.Parse()

    lis, err := net.Listen("tcp", *addr)
    if err != nil {
        log.Fatalf("listen: %v", err)
    }

    s := grpc.NewServer()

    // Health service
    hs := health.NewServer()
    healthpb.RegisterHealthServer(s, hs)

    // Register ingestion service if generated package is available.
    // Defer registration to internal/server to avoid build break before codegen.
    if err := ingester.Register(s); err != nil {
        log.Printf("ingestion registration skipped: %v", err)
    }

    go func() {
        log.Printf("ingester listening on %s", *addr)
        if err := s.Serve(lis); err != nil {
            log.Fatalf("serve: %v", err)
        }
    }()

    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
    defer stop()
    <-ctx.Done()
    log.Printf("shutting down...")
    s.GracefulStop()
}

func getEnv(k, def string) string {
    if v := os.Getenv(k); v != "" {
        return v
    }
    return def
}
package main

import (
	"flag"
	"fmt"
	"log"
	"net"

	"google.golang.org/grpc"
	canonicalv1 "github.com/cgb808/ZenGlowNext/dev-indexer_1/protos"
	canonical "github.com/cgb808/ZenGlowNext/dev-indexer_1/internal/canonical"
)

func main() {
	var (
		addr = flag.String("addr", ":50051", "listen address")
	)
	flag.Parse()

	lis, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	s := grpc.NewServer()
	// CanonicalService registration
	svc, err := canonical.NewServer(context.Background())
	if err != nil {
		log.Fatalf("canonical server init: %v", err)
	}
	defer svc.Close()
	canonicalv1.RegisterCanonicalServiceServer(s, svc)

	fmt.Printf("ingester listening on %s\n", *addr)
	if err := s.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
