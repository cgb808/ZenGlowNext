-- Final Knowledge Graph Schema (v6 minimal)
-- Purpose: Store discovered relationships between any two nodes (entities or events).

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id                 BIGSERIAL PRIMARY KEY,
    source_node        TEXT NOT NULL,   -- e.g., 'event:12345', 'user:abc-123'
    target_node        TEXT NOT NULL,
    relationship_type  TEXT NOT NULL,   -- e.g., 'correlates_with', 'causes_stress'
    strength           REAL,
    explanation        TEXT,
    discovered_by      TEXT NOT NULL,   -- 'ASO_Health_Swarm', 'LLM_Inference'
    created_at         TIMESTAMPTZ DEFAULT now()
);

-- Minimal index for common traversal
CREATE INDEX IF NOT EXISTS kg_source_node_idx ON knowledge_graph(source_node);
