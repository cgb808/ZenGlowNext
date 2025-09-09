package cache

import (
    "hash/fnv"
    "sync"
    "time"
)

const (
    numShards = 256
    entryTTL  = 5 * time.Minute
)

type entry struct {
    score      float64
    lastAccess time.Time
}

type shard struct {
    mu    sync.Mutex
    items map[string]*entry
}

// FreqTracker is a high-performance, concurrent frequency tracker with decay.
type FreqTracker struct {
    shards []*shard
    stopCh chan struct{}
}

// NewFreqTracker initializes a tracker and starts a background decay worker.
func NewFreqTracker(decayInterval time.Duration) *FreqTracker {
    ft := &FreqTracker{
        shards: make([]*shard, numShards),
        stopCh: make(chan struct{}),
    }
    for i := 0; i < numShards; i++ {
        ft.shards[i] = &shard{items: make(map[string]*entry)}
    }
    go ft.decayWorker(decayInterval)
    return ft
}

func (ft *FreqTracker) getShard(key string) *shard {
    h := fnv.New64a()
    _, _ = h.Write([]byte(key))
    return ft.shards[h.Sum64()%uint64(numShards)]
}

// Increment increases the score for a key and updates its last access.
func (ft *FreqTracker) Increment(key string) {
    s := ft.getShard(key)
    s.mu.Lock()
    defer s.mu.Unlock()
    if e, ok := s.items[key]; ok {
        e.score++
        e.lastAccess = time.Now()
    } else {
        s.items[key] = &entry{score: 1.0, lastAccess: time.Now()}
    }
}

// HotKeys returns up to limit keys whose scores meet the threshold.
func (ft *FreqTracker) HotKeys(threshold float64, limit int) []string {
    if limit <= 0 {
        return nil
    }
    out := make([]string, 0, limit)
    for _, s := range ft.shards {
        s.mu.Lock()
        for k, e := range s.items {
            if e.score >= threshold {
                out = append(out, k)
                if len(out) >= limit {
                    s.mu.Unlock()
                    return out
                }
            }
        }
        s.mu.Unlock()
    }
    return out
}

func (ft *FreqTracker) decayWorker(interval time.Duration) {
    t := time.NewTicker(interval)
    defer t.Stop()
    for {
        select {
        case <-t.C:
            now := time.Now()
            for _, s := range ft.shards {
                s.mu.Lock()
                for k, e := range s.items {
                    if now.Sub(e.lastAccess) > entryTTL {
                        delete(s.items, k)
                        continue
                    }
                    e.score *= 0.98
                    if e.score < 0.01 {
                        delete(s.items, k)
                    }
                }
                s.mu.Unlock()
            }
        case <-ft.stopCh:
            return
        }
    }
}

// Stop terminates the background decay worker.
func (ft *FreqTracker) Stop() { close(ft.stopCh) }
