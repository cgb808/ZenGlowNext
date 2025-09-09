package cache

import (
    "sync"

    lru "github.com/hashicorp/golang-lru/v2"
)

// HotCache is a small LRU used for hot items. It is concurrency-safe
// and supports runtime control (resize/clear) by a tooling agent.
type HotCache struct {
    mu  sync.RWMutex
    lru *lru.Cache[string, any]
}

func NewHotCache(size int) *HotCache {
    c, _ := lru.New[string, any](size)
    return &HotCache{lru: c}
}

func (h *HotCache) Get(key string) (any, bool) {
    h.mu.RLock()
    defer h.mu.RUnlock()
    return h.lru.Get(key)
}

func (h *HotCache) Set(key string, val any) {
    h.mu.Lock()
    defer h.mu.Unlock()
    h.lru.Add(key, val)
}

// Delete removes a key if present.
func (h *HotCache) Delete(key string) {
    h.mu.Lock()
    defer h.mu.Unlock()
    h.lru.Remove(key)
}

// Clear drops all entries.
func (h *HotCache) Clear() {
    h.mu.Lock()
    defer h.mu.Unlock()
    // Reinitialize to avoid per-key iteration cost.
    size := h.lru.Len()
    if size <= 0 {
        size = 1
    }
    c, _ := lru.New[string, any](size)
    h.lru = c
}

// Resize replaces the underlying LRU with a new capacity.
// Existing entries are dropped (simplest, predictable behavior).
func (h *HotCache) Resize(newSize int) {
    if newSize <= 0 {
        newSize = 1
    }
    h.mu.Lock()
    defer h.mu.Unlock()
    c, _ := lru.New[string, any](newSize)
    h.lru = c
}

// Len returns the number of items currently stored.
func (h *HotCache) Len() int {
    h.mu.RLock()
    defer h.mu.RUnlock()
    return h.lru.Len()
}
