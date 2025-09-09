package router

import (
    "context"
    "log"

    "github.com/go-redis/redis/v8"
    "github.com/jackc/pgx/v5/pgxpool"

    pb "github.com/cgb808/ZenGlowNext/grpc-router/internal/gen/services/router/v1"
    "github.com/cgb808/ZenGlowNext/grpc-router/internal/cache"
)

type Server struct {
    pb.UnimplementedRouterServiceServer
    pgPool *pgxpool.Pool
    redis  *redis.Client
    cache  *cache.HotCache
}

func NewServer(pg *pgxpool.Pool, rd *redis.Client) *Server {
    return &Server{pgPool: pg, redis: rd, cache: cache.NewHotCache(10000)}
}

func (s *Server) Process(ctx context.Context, req *pb.RequestEnvelope) (*pb.ResponseEnvelope, error) {
    log.Printf("req %s from %s", req.GetRequestId(), req.GetSourceService())
    // track frequency if desired with FreqTracker; not wired yet

    switch req.Payload.(type) {
    case *pb.RequestEnvelope_EmbedRequest:
        return s.handleEmbedRequest(ctx, req)
    case *pb.RequestEnvelope_AnalyzeEventRequest:
        return s.handleAnalysisRequest(ctx, req)
    default:
        return &pb.ResponseEnvelope{RequestId: req.GetRequestId(), Status: pb.ResponseEnvelope_ERROR, ErrorMessage: "unknown payload"}, nil
    }
}

func (s *Server) handleEmbedRequest(ctx context.Context, req *pb.RequestEnvelope) (*pb.ResponseEnvelope, error) {
    payload := req.GetEmbedRequest()
    key := "embedding:" + payload.GetTextToEmbed()

    if v, ok := s.cache.Get(key); ok {
        log.Printf("L1 HIT %s", key)
        if arr, ok := v.([]float32); ok {
            return okResp(req.GetRequestId(), &pb.ResponseEnvelope_EmbedResponse{EmbedResponse: &pb.EmbedResponse{Embedding: arr}}), nil
        }
    }

    if s.redis != nil {
        if raw, err := s.redis.Get(ctx, key).Bytes(); err == nil && len(raw) > 0 {
            log.Printf("L2 HIT %s", key)
            // TODO: deserialize raw (JSON or msgpack)
            // For blueprint, stub a small vector
            vec := []float32{0.1, 0.2, 0.3}
            go s.cache.Set(key, vec)
            return okResp(req.GetRequestId(), &pb.ResponseEnvelope_EmbedResponse{EmbedResponse: &pb.EmbedResponse{Embedding: vec}}), nil
        }
    }

    log.Printf("MISS %s -> embedding backend", key)
    // TODO: call downstream embedding service; stub response for now
    vec := []float32{0.1, 0.2, 0.3}
    go s.cache.Set(key, vec)
    // TODO: serialize and set to Redis with TTL
    return okResp(req.GetRequestId(), &pb.ResponseEnvelope_EmbedResponse{EmbedResponse: &pb.EmbedResponse{Embedding: vec}}), nil
}

func (s *Server) handleAnalysisRequest(ctx context.Context, req *pb.RequestEnvelope) (*pb.ResponseEnvelope, error) {
    // stub
    return &pb.ResponseEnvelope{RequestId: req.GetRequestId(), Status: pb.ResponseEnvelope_OK}, nil
}

func okResp(id string, payload any) *pb.ResponseEnvelope {
    switch p := payload.(type) {
    case *pb.ResponseEnvelope_EmbedResponse:
        return &pb.ResponseEnvelope{RequestId: id, Status: pb.ResponseEnvelope_OK, Payload: p}
    default:
        return &pb.ResponseEnvelope{RequestId: id, Status: pb.ResponseEnvelope_OK}
    }
}
