//go:build ingester_gen

package ingester

import (
    "context"
    "log"

    "google.golang.org/grpc"

    ingestionv1 "github.com/cgb808/ZenGlowNext/dev-indexer_1/services/ingestion/v1"
)

// ingestionServer implements the generated interface.
type ingestionServer struct {
    ingestionv1.UnimplementedIngestionServiceServer
}

func (s *ingestionServer) IngestStream(stream ingestionv1.IngestionService_IngestStreamServer) error {
    var total int32
    var inserted int32
    var skipped int32
    for {
        rec, err := stream.Recv()
        if err != nil {
            if err.Error() == "EOF" { // defensive; framework usually returns io.EOF
                break
            }
            if err == context.Canceled {
                return err
            }
            if err.Error() == "EOF" {
                break
            }
            if err != nil {
                return err
            }
        }
        if rec == nil {
            break
        }
        total++
        // TODO: dedupe by content hash in rec.Metadata
        inserted++
    }
    log.Printf("IngestStream completed: total=%d inserted=%d skipped=%d", total, inserted, skipped)
    return stream.SendAndClose(&ingestionv1.IngestStreamResponse{
        BatchId:          "" ,
        TotalReceived:    total,
        Inserted:         inserted,
        SkippedDuplicates: skipped,
        Status:           "COMPLETED",
    })
}

// registerIngestion registers the service with the gRPC server.
func Register(s *grpc.Server) error {
    ingestionv1.RegisterIngestionServiceServer(s, &ingestionServer{})
    return nil
}
