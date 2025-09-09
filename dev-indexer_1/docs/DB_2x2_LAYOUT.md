# 2x2 Database Layout

This project can run with four logical Postgres endpoints:

- Non-PII Vector (pgvector): DATABASE_URL_VEC
- Non-PII Timeseries (Timescale): DATABASE_URL_TS
- PII Vector (pgvector): PII_DATABASE_URL_VEC
- PII Timeseries (Timescale): PII_DATABASE_URL_TS

Defaults map to the two local Postgres containers defined in docker-compose:
- db (rag_db) on 127.0.0.1:5432
- db_pii (rag_pii) on 127.0.0.1:5433

If you don't override the 2x2 variables, both "_VEC" and "_TS" for a given privacy zone point to the same DSN, which is fine for dev.

## Quick start

- Copy .env.example to .env and adjust passwords.
- Optionally set the 2x2 DSNs in .env:
  - DATABASE_URL_VEC, DATABASE_URL_TS
  - PII_DATABASE_URL_VEC, PII_DATABASE_URL_TS
- docker compose up -d (the compose file mounts a number of SQL files into the Postgres init path)

## Applying schema

- Non-PII db mounts core schemas: artifact/rag/events/knowledge_graph, plus indexes (pgvector + JSONB + trigram).
- PII db mounts pii_secure_schema.sql (RLS, token map, access log).

## Service expectations

- Go CanonicalService reads DATABASE_URL_VEC (fallback to DATABASE_URL).
- Python FastAPI may use DATABASE_URL_* and PII_DATABASE_URL_* as we wire services; legacy variables remain for compatibility.

## Future

- FDW links between non-PII and PII will be read-only and narrowly scoped.
- Announce environment variable changes in docs when Router/Ingester services start using the split DSNs.
