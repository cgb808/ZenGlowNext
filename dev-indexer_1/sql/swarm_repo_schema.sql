-- Swarm Repository Schema (self-contained lifecycle + knowledge base)

-- Extensions and prerequisites
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums
DO $$ BEGIN
    CREATE TYPE swarm_topology AS ENUM ('star', 'ring', 'mesh');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE agent_role AS ENUM ('queen', 'worker', 'scout', 'explorer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Core swarms and agents
CREATE TABLE IF NOT EXISTS swarms (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  topology    swarm_topology NOT NULL,
  status      TEXT NOT NULL DEFAULT 'idle',
  purpose     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
  id              BIGSERIAL PRIMARY KEY,
  swarm_id        BIGINT REFERENCES swarms(id) ON DELETE CASCADE,
  role            agent_role NOT NULL,
  status          TEXT NOT NULL DEFAULT 'offline',
  container_id    TEXT,
  last_heartbeat  TIMESTAMPTZ,
  health_metrics  JSONB
);

-- Missions (modified with outcome and key_insight_node)
CREATE TABLE IF NOT EXISTS missions (
  id                BIGSERIAL PRIMARY KEY,
  assigned_swarm_id BIGINT REFERENCES swarms(id),
  status            TEXT NOT NULL DEFAULT 'pending',
  outcome           TEXT, -- 'win', 'loss', 'inconclusive'
  objective         JSONB NOT NULL,
  results_summary   JSONB,
  key_insight_node  TEXT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  completed_at      TIMESTAMPTZ
);

-- Activity log (time-partitioned)
CREATE TABLE IF NOT EXISTS activity_log (
  event_time    TIMESTAMPTZ NOT NULL,
  agent_id      BIGINT REFERENCES agents(id),
  mission_id    BIGINT REFERENCES missions(id),
  action        TEXT NOT NULL,
  details       JSONB
) PARTITION BY RANGE (event_time);

SELECT create_hypertable('activity_log', 'event_time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_activity_time_desc ON activity_log (event_time DESC);
CREATE INDEX IF NOT EXISTS ix_activity_agent_time ON activity_log (agent_id, event_time DESC);

-- Collective memory (pheromone trails)
CREATE TABLE IF NOT EXISTS pheromone_trails (
  id                    BIGSERIAL PRIMARY KEY,
  source_node           TEXT NOT NULL,
  target_node           TEXT NOT NULL,
  strength              REAL NOT NULL DEFAULT 0.1,
  decay_rate            REAL NOT NULL DEFAULT 0.01,
  last_reinforced_at    TIMESTAMPTZ,
  discovered_by_swarm_id BIGINT REFERENCES swarms(id)
);
CREATE INDEX IF NOT EXISTS pheromone_source_node_idx ON pheromone_trails(source_node);
CREATE INDEX IF NOT EXISTS pheromone_target_node_idx ON pheromone_trails(target_node);

-- Agent ancestry and traits (evolution)
CREATE TABLE IF NOT EXISTS agent_ancestry_and_traits (
  id                   BIGSERIAL PRIMARY KEY,
  agent_id             BIGINT REFERENCES agents(id) UNIQUE,
  base_model           TEXT NOT NULL,
  training_dataset_ref TEXT,
  hyperparameters      JSONB,
  parent_agent_id      BIGINT,
  generation           INT NOT NULL DEFAULT 1,
  created_at           TIMESTAMPTZ DEFAULT now()
);

-- Aggregated performance stats
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

-- Trigger to update stats when a mission completes
CREATE OR REPLACE FUNCTION update_agent_stats_on_mission_complete()
RETURNS TRIGGER AS $$
DECLARE
    mission_duration_ms REAL;
    agent_id_to_update BIGINT;
BEGIN
    SELECT id INTO agent_id_to_update FROM agents WHERE swarm_id = NEW.assigned_swarm_id LIMIT 1;
    IF agent_id_to_update IS NOT NULL THEN
        mission_duration_ms := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.created_at)) * 1000;
        INSERT INTO agent_performance_stats (
            agent_id, total_missions, wins, losses, avg_mission_time_ms, last_mission_at
        )
        VALUES (
            agent_id_to_update,
            1,
            CASE WHEN NEW.outcome = 'win' THEN 1 ELSE 0 END,
            CASE WHEN NEW.outcome = 'loss' THEN 1 ELSE 0 END,
            mission_duration_ms,
            NEW.completed_at
        )
        ON CONFLICT (agent_id) DO UPDATE SET
            total_missions = agent_performance_stats.total_missions + 1,
            wins = agent_performance_stats.wins + (CASE WHEN NEW.outcome = 'win' THEN 1 ELSE 0 END),
            losses = agent_performance_stats.losses + (CASE WHEN NEW.outcome = 'loss' THEN 1 ELSE 0 END),
            avg_mission_time_ms = ((COALESCE(agent_performance_stats.avg_mission_time_ms, 0) * agent_performance_stats.total_missions) + mission_duration_ms) / NULLIF(agent_performance_stats.total_missions + 1, 0),
            last_mission_at = NEW.completed_at,
            last_updated_at = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER mission_completed_trigger
    AFTER UPDATE OF status ON missions
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_agent_stats_on_mission_complete();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
