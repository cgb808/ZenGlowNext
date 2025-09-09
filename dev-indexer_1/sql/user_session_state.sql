-- Session continuity support: "pick up where we left off"
-- Keep keys text-based to avoid coupling to a specific users table

CREATE TABLE IF NOT EXISTS user_session_state (
  user_id              TEXT PRIMARY KEY,
  last_interaction_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_agent    TEXT,
  last_ai_response     TEXT,
  last_topic_summary   TEXT,
  conversation_context JSONB
);

CREATE INDEX IF NOT EXISTS idx_user_session_state_last_interaction ON user_session_state (last_interaction_at DESC);
