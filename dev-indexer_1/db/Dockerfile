# Multi-feature Postgres image: TimescaleDB + pgvector on Postgres 15
FROM timescale/timescaledb-ha:pg15-latest
# Multi-feature Postgres image: TimescaleDB + pgvector on Postgres 15
FROM timescale/timescaledb-ha:pg15-latest

# Install pgvector extension
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-15-pgvector \
 && rm -rf /var/lib/apt/lists/*

USER postgres
# timescaledb-ha already configures shared_preload_libraries for timescaledb
# pgvector does not require preload
# Install pgvector extension
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-15-pgvector \
 && rm -rf /var/lib/apt/lists/*

USER postgres
# timescaledb-ha already configures shared_preload_libraries for timescaledb
# pgvector does not require preload

