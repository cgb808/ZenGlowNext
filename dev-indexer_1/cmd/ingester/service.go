package main

import (
	"context"
	"io"
	"log"

	// pb "zenglow/ingester/gen/ingestion/v1"
)

// IngestionServer implements the gRPC service.
type IngestionServer struct {
	// pb.UnimplementedIngestionServiceServer
	// dbPool *pgxpool.Pool
	// embedderClient EmbedderClient
}

// func newServer() *IngestionServer { return &IngestionServer{} }

// IngestStream is the server-side implementation of the streaming RPC.
// func (s *IngestionServer) IngestStream(stream pb.IngestionService_IngestStreamServer) error {
// 	var receivedCount, insertedCount, skippedCount int32
// 	var batch []*pb.IngestRecord
// 
// 	for {
// 		rec, err := stream.Recv()
// 		if err == io.EOF {
// 			// TODO: process remaining batch
// 			return stream.SendAndClose(&pb.IngestStreamResponse{
// 				TotalReceived:     receivedCount,
// 				Inserted:          insertedCount,
// 				SkippedDuplicates: skippedCount,
// 				Status:            "COMPLETED",
// 			})
// 		}
// 		if err != nil {
// 			return err
// 		}
// 		receivedCount++
// 
// 		// TODO: hash/dedupe, embed if missing, add to batch
// 		batch = append(batch, rec)
// 
// 		if len(batch) >= 100 {
// 			// TODO: embed, dedupe, and insert with copy
// 			log.Printf("processing batch of %d", len(batch))
// 			batch = nil
// 		}
// 	}
// }

func dummy(_ context.Context) { log.Println("placeholder") }
