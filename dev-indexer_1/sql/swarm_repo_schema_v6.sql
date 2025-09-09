-- =============================================================
-- Final Consolidated Schema (v6 - Performance & Evolution Optimized)
-- Swarm repo + knowledge_graph (idempotent)
-- =============================================================

-- 1) Custom Types
DO $$ BEGIN
  CREATE TYPE swarm_topology AS ENUM ('star', 'ring', 'mesh');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE agent_role AS ENUM ('queen', 'worker', 'scout', 'explorer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 2) Core Swarm & Agents
CREATE TABLE IF NOT EXISTS swarms (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  topology    swarm_topology NOT NULL,
  status      TEXT NOT NULL DEFAULT 'idle',
  purpose     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
  id             BIGSERIAL PRIMARY KEY,
  swarm_id       BIGINT REFERENCES swarms(id) ON DELETE CASCADE,
  role           agent_role NOT NULL,
  status         TEXT NOT NULL DEFAULT 'offline',
  container_id   TEXT,
  last_heartbeat TIMESTAMPTZ,
  health_metrics JSONB
);
CREATE INDEX IF NOT EXISTS idx_agents_swarm_id ON agents(swarm_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- 3) Missions & Performance
CREATE TABLE IF NOT EXISTS missions (
  id                 BIGSERIAL PRIMARY KEY,
  assigned_swarm_id  BIGINT REFERENCES swarms(id),
  status             TEXT NOT NULL DEFAULT 'pending',
  outcome            TEXT,
  objective          JSONB NOT NULL,
  results_summary    JSONB,
  key_insight_node   TEXT,
  created_at         TIMESTAMPTZ DEFAULT now(),
  completed_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_missions_swarm_status ON missions(assigned_swarm_id, status);
CREATE INDEX IF NOT EXISTS idx_missions_created_at ON missions(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_performance_stats (
  agent_id            BIGINT PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
  total_missions      INT NOT NULL DEFAULT 0,
  wins                INT NOT NULL DEFAULT 0,
  losses              INT NOT NULL DEFAULT 0,
  win_loss_ratio      REAL GENERATED ALWAYS AS (wins / NULLIF(losses, 0)::float) STORED,
  avg_mission_time_ms REAL,
  last_mission_at     TIMESTAMPTZ,
  last_updated_at     TIMESTAMPTZ DEFAULT now()
);

-- 4) Agent Evolution & Knowledge Graph
CREATE TABLE IF NOT EXISTS agent_ancestry_and_traits (
  id              BIGSERIAL PRIMARY KEY,
  agent_id        BIGINT UNIQUE REFERENCES agents(id),
  base_model      TEXT NOT NULL,
  hyperparameters JSONB,
  parent_agent_id BIGINT,
  generation      INT NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_graph (
  id                BIGSERIAL PRIMARY KEY,
  source_node       TEXT NOT NULL,
  target_node       TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  strength          REAL,
  explanation       TEXT,
  discovered_by     TEXT NOT NULL,
  created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS kg_source_node_idx ON knowledge_graph(source_node);
CREATE INDEX IF NOT EXISTS kg_target_node_idx ON knowledge_graph(target_node);
CREATE INDEX IF NOT EXISTS kg_rel_type_idx ON knowledge_graph(relationship_type);

-- 5) Activity Log (partitioned by time; managed externally e.g., pg_partman)
CREATE TABLE IF NOT EXISTS activity_log (
  event_time TIMESTAMPTZ NOT NULL,
  agent_id   BIGINT REFERENCES agents(id),
  mission_id BIGINT REFERENCES missions(id),
  action     TEXT NOT NULL,
  details    JSONB
) PARTITION BY RANGE (event_time);

-- 6) Trigger stub for mission completion → performance update
CREATE OR REPLACE FUNCTION update_agent_stats_on_mission_complete()
RETURNS TRIGGER AS $$
BEGIN
  -- NOTE: Implement UPSERT to increment stats and compute duration.
  -- This stub logs intent only; adapt per your mission→agent mapping.
  RAISE NOTICE 'Triggered to update stats for mission %', NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS mission_completed_trigger ON missions;
CREATE TRIGGER mission_completed_trigger
AFTER UPDATE OF status ON missions
FOR EACH ROW
WHEN (NEW.status = 'completed')
EXECUTE FUNCTION update_agent_stats_on_mission_complete();
