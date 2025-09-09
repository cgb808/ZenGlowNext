package main

import (
    "context"
    "flag"
    "log"
    "net"
    "os"

    "github.com/go-redis/redis/v8"
    "github.com/jackc/pgx/v5/pgxpool"
    "google.golang.org/grpc"

    pb "github.com/cgb808/ZenGlowNext/grpc-router/internal/gen/services/router/v1"
    "github.com/cgb808/ZenGlowNext/grpc-router/internal/router"
)

func mustEnv(key, def string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return def
}

func main() {
    addr := flag.String("addr", mustEnv("ROUTER_ADDR", ":50051"), "gRPC listen address")
    dbURL := flag.String("DATABASE_URL", mustEnv("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/postgres"), "Postgres URL")
    redisURL := flag.String("REDIS_URL", mustEnv("REDIS_URL", "redis://localhost:6379/0"), "Redis URL")
    flag.Parse()

    // Postgres pool
    cfg, err := pgxpool.ParseConfig(*dbURL)
    if err != nil { log.Fatalf("invalid DATABASE_URL: %v", err) }
    pgPool, err := pgxpool.NewWithConfig(context.Background(), cfg)
    if err != nil { log.Fatalf("pgx pool: %v", err) }
    defer pgPool.Close()

    // Redis client
    opt, err := redis.ParseURL(*redisURL)
    if err != nil { log.Fatalf("invalid REDIS_URL: %v", err) }
    rdb := redis.NewClient(opt)
    if err := rdb.Ping(context.Background()).Err(); err != nil { log.Fatalf("redis ping: %v", err) }

    // gRPC server
    s := grpc.NewServer()
    srv := router.NewServer(pgPool, rdb)
    pb.RegisterRouterServiceServer(s, srv)

    lis, err := net.Listen("tcp", *addr)
    if err != nil { log.Fatalf("listen: %v", err) }
    log.Printf("router listening on %s", *addr)
    if err := s.Serve(lis); err != nil { log.Fatalf("grpc serve: %v", err) }
}
