package main

import (
    "context"
    "flag"
    "fmt"
    "log"
    "time"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    canonicalv1 "github.com/cgb808/ZenGlowNext/dev-indexer_1/protos"
)

func main() {
    addr := flag.String("addr", "localhost:50051", "gRPC server address")
    text := flag.String("text", "hello world", "query text")
    topk := flag.Int("k", 5, "top K")
    flag.Parse()

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    conn, err := grpc.DialContext(ctx, *addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
    if err != nil { log.Fatalf("dial: %v", err) }
    defer conn.Close()

    c := canonicalv1.NewCanonicalServiceClient(conn)
    resp, err := c.TopKEvents(ctx, &canonicalv1.TopKQueryRequest{Text: *text, TopK: uint32(*topk)})
    if err != nil { log.Fatalf("TopKEvents: %v", err) }
    for i, r := range resp.GetResults() {
        fmt.Printf("%d) score=%.4f type=%s time=%s token=%s\n", i+1, r.GetScore(), r.GetEvent().GetEventType(), r.GetEvent().GetEventTime(), r.GetEvent().GetUserToken())
    }
}
