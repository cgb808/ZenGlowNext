package server

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"github.com/klauspost/compress/zstd"
	redis "github.com/redis/go-redis/v9"
	loggingv1 "github.com/cgb808/ZenGlowNext/grpc/logservice/internal/gen/services/logging/v1"
)

type LogServer struct {
	loggingv1.UnimplementedLogServiceServer
	mu             sync.Mutex
	sessionWriters map[string]chan *loggingv1.LogFrame
}

func NewLogServer() *LogServer {
	return &LogServer{sessionWriters: make(map[string]chan *loggingv1.LogFrame)}
}

func (s *LogServer) WriteLogStream(stream loggingv1.LogService_WriteLogStreamServer) error {
	var count uint32
	for {
		frame, err := stream.Recv()
		if err == io.EOF {
			return stream.SendAndClose(&loggingv1.WriteLogResponse{FramesReceived: count, Status: "ACKNOWLEDGED"})
		}
		if err != nil {
			return err
		}
		ch := s.getOrCreateWriter(frame.GetSessionId())
		select {
		case ch <- frame:
			count++
		default:
			// simple backpressure: drop oldest by draining one then push
			<-ch
			ch <- frame
		}
	}
}

func (s *LogServer) getOrCreateWriter(sessionID string) chan *loggingv1.LogFrame {
	s.mu.Lock()
	defer s.mu.Unlock()
	if ch, ok := s.sessionWriters[sessionID]; ok {
		return ch
	}
	ch := make(chan *loggingv1.LogFrame, 1024)
	s.sessionWriters[sessionID] = ch
	go sessionFileWriter(sessionID, ch)
	return ch
}

type writerConfig struct {
	Dir           string
	MaxSize       int64
	Compress      bool
	ZstdLevel     int
	Fsync         bool
	RedisURL      string
	RedisListKey  string
	RedisListTTL  time.Duration
}

func envOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func loadConfig() writerConfig {
	maxSize, _ := strconv.ParseInt(envOrDefault("LOG_MAX_SIZE_BYTES", "1048576"), 10, 64)
	zstdLvl, _ := strconv.Atoi(envOrDefault("LOG_ZSTD_LEVEL", "3"))
	fsync := envOrDefault("LOG_FSYNC", "0") == "1"
	ttlSeconds, _ := strconv.Atoi(envOrDefault("LOG_REDIS_TTL_SECONDS", "0"))
	return writerConfig{
		Dir:          envOrDefault("LOG_DIR", "data/append_logs"),
		MaxSize:      maxSize,
		Compress:     envOrDefault("LOG_COMPRESS", "zstd") == "zstd",
		ZstdLevel:    zstdLvl,
		Fsync:        fsync,
		RedisURL:     envOrDefault("REDIS_URL", "redis://localhost:6379/0"),
		RedisListKey: envOrDefault("LOG_REDIS_LIST", "append:segments"),
		RedisListTTL: time.Duration(ttlSeconds) * time.Second,
	}
}

func sessionFileWriter(sessionID string, frames <-chan *loggingv1.LogFrame) {
	cfg := loadConfig()
	_ = os.MkdirAll(cfg.Dir, 0o755)
	log.Printf("writer start: %s dir=%s max=%dB compress=%v zstd_level=%d", sessionID, cfg.Dir, cfg.MaxSize, cfg.Compress, cfg.ZstdLevel)

	// Redis client (optional)
	var rdb *redis.Client
	if cfg.RedisURL != "" {
		opt, err := redis.ParseURL(cfg.RedisURL)
		if err == nil {
			rdb = redis.NewClient(opt)
		} else {
			log.Printf("[redis] parse failed: %v", err)
		}
	}

	// State
	base := filepath.Join(cfg.Dir, "session_"+sessionID)
	seqPath := base + ".seq"
	tmpPath := base + ".logtmp"
	zstPath := base + ".log.zst"
	var seq int64
	if b, err := os.ReadFile(seqPath); err == nil {
		if v, e := strconv.ParseInt(string(b), 10, 64); e == nil { seq = v }
	}

	// Open temp file
	f, err := os.OpenFile(tmpPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil { log.Printf("open tmp failed: %v", err); return }
	bw := bufio.NewWriterSize(f, 64*1024)

	// Helpers
	writeFrame := func(fr *loggingv1.LogFrame) error {
		// allocate seq if missing
		if fr.Seq == 0 { seq++; fr.Seq = seq }
		// write line-delimited JSON
		m := map[string]any{
			"time": fr.Time.AsTime().UnixNano(),
			"seq":  fr.Seq,
			"user": fr.UserId,
			"role": fr.Role,
			"content": fr.Content,
		}
		b, _ := json.Marshal(m)
		if _, err := bw.Write(b); err != nil { return err }
		if err := bw.WriteByte('\n'); err != nil { return err }
		return nil
	}

	rotate := func() error {
		if err := bw.Flush(); err != nil { return err }
		if cfg.Fsync { _ = f.Sync() }
		if err := f.Close(); err != nil { return err }
		// compress to .zst
		if cfg.Compress {
			dst, err := os.Create(zstPath)
			if err != nil { return err }
			enc, err := zstd.NewWriter(dst, zstd.WithEncoderLevel(zstd.EncoderLevelFromZstd(cfg.ZstdLevel)))
			if err != nil { _ = dst.Close(); return err }
			src, err := os.Open(tmpPath)
			if err != nil { enc.Close(); _ = dst.Close(); return err }
			if _, err = io.Copy(enc, src); err != nil { enc.Close(); _ = dst.Close(); _ = src.Close(); return err }
			enc.Close(); _ = src.Close(); _ = dst.Close()
			// remove original
			_ = os.Remove(tmpPath)
			// push path to redis
			if rdb != nil {
				ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
				defer cancel()
				if err := rdb.RPush(ctx, cfg.RedisListKey, zstPath).Err(); err != nil {
					log.Printf("[queue] push failed: %v", err)
				} else {
					log.Printf("[queue] %s -> %s", filepath.Base(zstPath), cfg.RedisListKey)
					if cfg.RedisListTTL > 0 {
						// Set TTL only when list becomes empty later is handled by consumer; here we can set a base TTL
						_ = rdb.Expire(ctx, cfg.RedisListKey, cfg.RedisListTTL).Err()
					}
				}
			}
		}
		// re-open fresh tmp
		nf, err := os.OpenFile(tmpPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
		if err != nil { return err }
		f = nf
		bw.Reset(f)
		// persist seq
		_ = os.WriteFile(seqPath, []byte(strconv.FormatInt(seq, 10)), 0o644)
		return nil
	}

	// Loop
	var curSize int64
	if st, err := os.Stat(tmpPath); err == nil { curSize = st.Size() }
	for fr := range frames {
		if err := writeFrame(fr); err != nil {
			log.Printf("write err: %v", err)
			continue
		}
		curSize += int64(len(fr.Content))
		if curSize >= cfg.MaxSize {
			if err := rotate(); err != nil {
				log.Printf("rotate err: %v", err)
			} else {
				log.Printf("[append] %s seq=%d size=%d fsync=%v rotated=True", sessionID, seq, curSize, cfg.Fsync)
			}
			curSize = 0
		}
	}
	// final flush
	_ = bw.Flush()
	if cfg.Fsync { _ = f.Sync() }
	_ = f.Close()
	log.Printf("writer stop: %s", sessionID)
}
