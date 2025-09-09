-- Swarm Repository Schema (ASO swarms lifecycle + knowledge)

-- Enums
DO $$ BEGIN
		CREATE TYPE swarm_topology AS ENUM ('star', 'ring', 'mesh');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
		CREATE TYPE agent_role AS ENUM ('queen', 'worker', 'scout', 'explorer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Core
CREATE TABLE IF NOT EXISTS swarms (
	id          BIGSERIAL PRIMARY KEY,
	name        TEXT UNIQUE NOT NULL,
	topology    swarm_topology NOT NULL,
	status      TEXT NOT NULL DEFAULT 'idle',  -- idle, active, maintenance
	purpose     TEXT NOT NULL,
	owner_identity_id UUID  -- references pii_identity_profiles(id) in PII vault (logical reference)
);

-- Ensure column exists when table pre-existed
DO $$ BEGIN
    ALTER TABLE swarms ADD COLUMN IF NOT EXISTS owner_identity_id UUID;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS ix_swarms_owner ON swarms(owner_identity_id);

CREATE TABLE IF NOT EXISTS agents (
	id              BIGSERIAL PRIMARY KEY,
	swarm_id        BIGINT REFERENCES swarms(id) ON DELETE CASCADE,
	role            agent_role NOT NULL,
	status          TEXT NOT NULL DEFAULT 'offline',  -- offline, online, processing
	container_id    TEXT,
	last_heartbeat  TIMESTAMPTZ,
	health_metrics  JSONB,
	owner_identity_id UUID
);

DO $$ BEGIN
    ALTER TABLE agents ADD COLUMN IF NOT EXISTS owner_identity_id UUID;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS ix_agents_owner ON agents(owner_identity_id);

-- Missions (modified with outcome, key_insight_node)
CREATE TABLE IF NOT EXISTS missions (
	id                BIGSERIAL PRIMARY KEY,
	assigned_swarm_id BIGINT REFERENCES swarms(id),
	status            TEXT NOT NULL DEFAULT 'pending',
	outcome           TEXT,  -- 'win', 'loss', 'inconclusive'
	objective         JSONB NOT NULL,
	results_summary   JSONB,
	key_insight_node  TEXT,
	created_at        TIMESTAMPTZ DEFAULT now(),
	completed_at      TIMESTAMPTZ,
	owner_identity_id UUID
);

DO $$ BEGIN
    ALTER TABLE missions ADD COLUMN IF NOT EXISTS owner_identity_id UUID;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS ix_missions_owner ON missions(owner_identity_id);

-- Activity log (native partitioning; manage with pg_partman)
CREATE TABLE IF NOT EXISTS activity_log (
	event_time    TIMESTAMPTZ NOT NULL,
	agent_id      BIGINT REFERENCES agents(id),
	mission_id    BIGINT REFERENCES missions(id),
	action        TEXT NOT NULL,
	details       JSONB
) PARTITION BY RANGE (event_time);

-- Note: pheromone_trails table removed in v6 simplified schema.

-- Agent genetics/evolution
CREATE TABLE IF NOT EXISTS agent_ancestry_and_traits (
	id                    BIGSERIAL PRIMARY KEY,
	agent_id              BIGINT REFERENCES agents(id) UNIQUE,
	base_model            TEXT NOT NULL,
	hyperparameters       JSONB,
	parent_agent_id       BIGINT,
	generation            INT NOT NULL DEFAULT 1,
	created_at            TIMESTAMPTZ DEFAULT now()
);

-- Aggregated performance
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

-- Trigger to update stats on mission completion
CREATE OR REPLACE FUNCTION update_agent_stats_on_mission_complete()
RETURNS TRIGGER AS $$
DECLARE
	v_agent_id BIGINT;
	v_duration_ms REAL;
BEGIN
	-- Derive an agent_id if available via activity_log or mission results
	-- Fallback: NULL safe handling; only update when we can associate an agent
	SELECT agent_id INTO v_agent_id
	FROM activity_log
	WHERE mission_id = NEW.id
	ORDER BY event_time DESC
	LIMIT 1;

	IF v_agent_id IS NULL THEN
		-- No agent association; skip stats update
		RETURN NEW;
	END IF;

	IF NEW.completed_at IS NOT NULL AND NEW.created_at IS NOT NULL THEN
		v_duration_ms := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.created_at)) * 1000.0;
	ELSE
		v_duration_ms := NULL;
	END IF;

	-- Upsert/update aggregate stats
	INSERT INTO agent_performance_stats AS s (agent_id, total_missions, wins, losses, avg_mission_time_ms, last_mission_at, last_updated_at)
	VALUES (
		v_agent_id,
		1,
		CASE WHEN NEW.outcome = 'win' THEN 1 ELSE 0 END,
		CASE WHEN NEW.outcome = 'loss' THEN 1 ELSE 0 END,
		v_duration_ms,
		NEW.completed_at,
		NOW()
	)
	ON CONFLICT (agent_id) DO UPDATE SET
		total_missions = s.total_missions + 1,
		wins = s.wins + EXCLUDED.wins,
		losses = s.losses + EXCLUDED.losses,
		avg_mission_time_ms = CASE
			WHEN s.avg_mission_time_ms IS NULL AND EXCLUDED.avg_mission_time_ms IS NOT NULL THEN EXCLUDED.avg_mission_time_ms
			WHEN s.avg_mission_time_ms IS NOT NULL AND EXCLUDED.avg_mission_time_ms IS NULL THEN s.avg_mission_time_ms
			WHEN s.avg_mission_time_ms IS NOT NULL AND EXCLUDED.avg_mission_time_ms IS NOT NULL THEN (s.avg_mission_time_ms + EXCLUDED.avg_mission_time_ms) / 2.0
			ELSE s.avg_mission_time_ms
		END,
		last_mission_at = COALESCE(EXCLUDED.last_mission_at, s.last_mission_at),
		last_updated_at = NOW();

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS mission_completed_trigger ON missions;
CREATE TRIGGER mission_completed_trigger
AFTER UPDATE OF status ON missions
FOR EACH ROW
WHEN (NEW.status = 'completed')
EXECUTE FUNCTION update_agent_stats_on_mission_complete();

