-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
-- timescaledb is optional for events partitioning; enable only if available in your cloud plan
-- CREATE EXTENSION IF NOT EXISTS timescaledb;