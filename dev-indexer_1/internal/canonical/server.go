package canonical

import (
    "context"
    "errors"
    "fmt"
    "os"
    "strings"
    "time"

    "github.com/jackc/pgx/v5/pgxpool"
    canonicalv1 "github.com/cgb808/ZenGlowNext/dev-indexer_1/protos"
)

type Server struct {
    canonicalv1.UnimplementedCanonicalServiceServer
    db *pgxpool.Pool
}

func NewServer(ctx context.Context) (*Server, error) {
    // Prefer dedicated vector DSN when provided; fall back to legacy DATABASE_URL
    dsn := os.Getenv("DATABASE_URL_VEC")
    if dsn == "" {
        dsn = os.Getenv("DATABASE_URL")
    }
    if dsn == "" {
        // Mock mode: allow server to start without DB for smoke tests
        return &Server{db: nil}, nil
    }
    pool, err := pgxpool.New(ctx, dsn)
    if err != nil {
        return nil, fmt.Errorf("pgxpool: %w", err)
    }
    return &Server{db: pool}, nil
}

func (s *Server) Close() { if s.db != nil { s.db.Close() } }

func (s *Server) TopKEvents(ctx context.Context, req *canonicalv1.TopKQueryRequest) (*canonicalv1.TopKQueryResponse, error) {
    topK := int(req.GetTopK())
    if topK <= 0 || topK > 100 { topK = 5 }

    // simple embedding stub if only text provided
    emb := req.GetEmbedding()
    if len(emb) == 0 && strings.TrimSpace(req.GetText()) != "" {
        emb = embedTextStub(req.GetText())
    }
    if len(emb) == 0 {
        // No embedding or text → empty
        return &canonicalv1.TopKQueryResponse{}, nil
    }

    if s.db == nil {
        // Return synthetic results in mock mode
        now := time.Now().UTC().Format(time.RFC3339)
        out := &canonicalv1.TopKQueryResponse{}
        for i := 0; i < topK; i++ {
            out.Results = append(out.Results, &canonicalv1.ScoredEvent{
                Event: &canonicalv1.Event{
                    EventTime:      now,
                    UserToken:      "mock-token",
                    AgentKey:       "mock-agent",
                    DeviceKey:      "mock-device",
                    EventType:      "mock",
                    DataPayloadProc: "{}",
                },
                Score: 0.99,
            })
        }
        return out, nil
    }

    // Build filters
    filters := []string{"event_embedding IS NOT NULL"}
    args := []any{emb}
    if ut := strings.TrimSpace(req.GetUserToken()); ut != "" {
        filters = append(filters, "user_token = $2")
        args = append(args, ut)
    }
    if et := strings.TrimSpace(req.GetEventType()); et != "" {
        filters = append(filters, fmt.Sprintf("event_type = $%d", len(args)+1))
        args = append(args, et)
    }
    where := strings.Join(filters, " AND ")

    // cosine distance: use <=> operator (pgvector) ascending
    // Note: $1::vector binds embedding; ensure pgx maps float32/64 slice correctly
    q := fmt.Sprintf(`
        SELECT event_time, user_token, agent_key, device_key, event_type,
               data_payload_proc::text,
               1 - (event_embedding <=> $1::vector) AS score
        FROM events
        WHERE %s
        ORDER BY (event_embedding <=> $1::vector) ASC
        LIMIT %d
    `, where, topK)

    rows, err := s.db.Query(ctx, q, args...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    resp := &canonicalv1.TopKQueryResponse{}
    for rows.Next() {
        var ev canonicalv1.Event
        var score float32
        var payload string
        if err := rows.Scan(&ev.EventTime, &ev.UserToken, &ev.AgentKey, &ev.DeviceKey, &ev.EventType, &payload, &score); err != nil {
            return nil, err
        }
        ev.DataPayloadProc = payload
        resp.Results = append(resp.Results, &canonicalv1.ScoredEvent{Event: &ev, Score: score})
    }
    return resp, nil
}

// embedTextStub is a tiny placeholder that returns a fixed-size zero vector with a simple hash-based jitter
func embedTextStub(text string) []float32 {
    dim := 768
    out := make([]float32, dim)
    var h uint32
    for i := 0; i < len(text); i++ { h = h*16777619 ^ uint32(text[i]) }
    base := float32(h%1000) / 1000.0
    for i := 0; i < dim; i++ { out[i] = base }
    return out
}
