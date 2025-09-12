-- Colony Swarm Schema (idempotent)
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;

-- Core: Colonies
CREATE TABLE IF NOT EXISTS colonies (
    colony_id SERIAL PRIMARY KEY,
    colony_type TEXT NOT NULL,  -- 'star', 'ring', 'explorer'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ants live in colonies
CREATE TABLE IF NOT EXISTS ants (
    ant_id SERIAL PRIMARY KEY,
    colony_id INT REFERENCES colonies(colony_id) ON DELETE CASCADE,
    behavior TEXT,  -- e.g. "pathfinder", "optimizer", "scout"
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Each run is a search / optimization attempt
CREATE TABLE IF NOT EXISTS runs (
    run_id SERIAL PRIMARY KEY,
    colony_id INT REFERENCES colonies(colony_id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- Vector results logged for each attempt
CREATE TABLE IF NOT EXISTS run_results (
    result_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    ant_id INT REFERENCES ants(ant_id),
    query_vector VECTOR(1536),       -- pgvector, adjust dimension
    result_vector VECTOR(1536),      -- what it found
    similarity FLOAT,
    success BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance metrics per run
CREATE TABLE IF NOT EXISTS run_metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    success_ratio FLOAT,        -- successes / total attempts
    avg_similarity FLOAT,
    exploration_score FLOAT,    -- how much unexplored space was covered
    exploitation_score FLOAT,   -- how well it reinforced good paths
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Colony evolution history (who’s winning)
CREATE TABLE IF NOT EXISTS colony_performance (
    perf_id SERIAL PRIMARY KEY,
    colony_id INT REFERENCES colonies(colony_id) ON DELETE CASCADE,
    total_runs INT,
    total_successes INT,
    avg_success_ratio FLOAT,
    best_similarity FLOAT,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Optional: for auto-analysis & cloning
CREATE TABLE IF NOT EXISTS colony_clones (
    clone_id SERIAL PRIMARY KEY,
    source_colony_id INT REFERENCES colonies(colony_id),
    new_colony_id INT REFERENCES colonies(colony_id),
    reason TEXT,  -- e.g. "success ratio > 0.8"
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings (pgvector)
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    shard_id INT NOT NULL,
    vector VECTOR(768), -- adjust dimension to your embedding size
    metadata JSONB
);

-- Pheromone matrix (per colony, per shard)
CREATE TABLE IF NOT EXISTS pheromones (
    id BIGSERIAL PRIMARY KEY,
    colony_type TEXT NOT NULL,   -- 'star', 'ring', 'explorer'
    shard_id INT NOT NULL,
    level DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    last_update TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (colony_type, shard_id)
);

-- Query history (for novelty bonuses in explorer colony)
CREATE TABLE IF NOT EXISTS query_history (
    id BIGSERIAL PRIMARY KEY,
    query_vector VECTOR(768),
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    shards_hit INT[],
    results JSONB
);

-- Track colony performance per query
CREATE TABLE IF NOT EXISTS colony_metrics (
    id BIGSERIAL PRIMARY KEY,
    query_id BIGINT,
    colony_type TEXT NOT NULL,         -- 'star', 'ring', 'explorer'
    num_ants INT NOT NULL,
    hits INT NOT NULL,                 -- number of results returned
    successes INT NOT NULL,            -- number of relevant results (cosine dist < threshold)
    failures INT NOT NULL,             -- results that were poor
    avg_distance DOUBLE PRECISION,
    latency_ms DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Aggregate stats (rolling metrics)
CREATE MATERIALIZED VIEW IF NOT EXISTS colony_stats AS
SELECT
    colony_type,
    count(*) as queries,
    sum(successes) as total_successes,
    sum(failures) as total_failures,
    avg(avg_distance) as mean_distance,
    avg(latency_ms) as mean_latency
FROM colony_metrics
GROUP BY colony_type;
