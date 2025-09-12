-- Role & Privilege Strategy (idempotent)
-- Provides tiered access:
--  * rag_read  : SELECT only
--  * rag_write : SELECT + INSERT + UPDATE (no DELETE)
--  * rag_admin : Full DML (SELECT/INSERT/UPDATE/DELETE/TRUNCATE) + can manage future tables' DML via default privileges
-- Passwords here are placeholders; rotate immediately in production.

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rag_base') THEN
  CREATE ROLE rag_base NOLOGIN;
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rag_read') THEN
  CREATE ROLE rag_read LOGIN PASSWORD 'change_me_read';
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rag_write') THEN
  CREATE ROLE rag_write LOGIN PASSWORD 'change_me_write';
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rag_admin') THEN
  CREATE ROLE rag_admin LOGIN PASSWORD 'change_me_admin';
END IF; END $$;

-- Membership (if you later decide to use inheritance, adjust INHERIT flags)
GRANT rag_base TO rag_read;
GRANT rag_base TO rag_write;
GRANT rag_base TO rag_admin;

-- Database level: allow connect
GRANT CONNECT ON DATABASE rag_db TO rag_read, rag_write, rag_admin;

-- Schema usage
GRANT USAGE ON SCHEMA public TO rag_read, rag_write, rag_admin;

-- Table privileges (existing tables)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_read;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rag_write;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public TO rag_admin;

-- Future tables: default privileges (executed by current role; run as owner)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rag_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO rag_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO rag_admin;

-- Sequences (needed if we insert into BIGSERIAL owning sequences)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rag_read;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rag_write, rag_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO rag_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO rag_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO rag_admin;

-- Optional: restrict DELETE for write role explicitly (redundant, but documents intent) by not granting it.

-- NOTE: Rotate passwords post-deploy:
-- ALTER ROLE rag_read  PASSWORD 'new_secret';
-- ALTER ROLE rag_write PASSWORD 'new_secret';
-- ALTER ROLE rag_admin PASSWORD 'new_secret';

-- To revoke unwanted rights later:
-- REVOKE UPDATE ON TABLE doc_embeddings FROM rag_read;  -- example
