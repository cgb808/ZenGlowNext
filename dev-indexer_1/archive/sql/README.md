This folder contains archived SQL files that have been superseded by canonical scripts in the `sql/` directory.

Archived files:
- roles_privileges.sql — duplicate of `sql/init.sql` (kept here for historical reference). Use `sql/init.sql` instead.
- pgvector_indexes.sql — superseded by comprehensive `sql/rag_indexes.sql` which creates ANN and supporting indexes across schemas.

Canonical scripts to use going forward:
- sql/init.sql — base pgvector extension + legacy `doc_embeddings` table and ANN index with HNSW→IVFFlat fallback.
- sql/rag_indexes.sql — unified index suite for RAG/Timescale tables, including vector and text search indexes.

These archived files are not referenced by the deploy process and may be removed in a future cleanup.
