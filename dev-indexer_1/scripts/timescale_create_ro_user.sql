-- Create a read-only user for FDW access from Supabase
-- Run this on the Timescale (core) database as a superuser

DO $$ BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = current_setting('app.fdw_ro_user', true)) THEN
      EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', current_setting('app.fdw_ro_user', true), current_setting('app.fdw_ro_pass', true));
   END IF;
END $$;

GRANT USAGE ON SCHEMA public TO PUBLIC; -- minimally allow schema usage

-- Grant select on the specific tables needed
GRANT SELECT ON TABLE public.events TO PUBLIC;
GRANT SELECT ON TABLE public.activity_log TO PUBLIC;

-- Alternatively, limit to the FDW user only (safer):
-- REVOKE ALL ON TABLE public.events FROM PUBLIC;
-- REVOKE ALL ON TABLE public.activity_log FROM PUBLIC;
-- GRANT SELECT ON TABLE public.events TO :fdw_user;
-- GRANT SELECT ON TABLE public.activity_log TO :fdw_user;
