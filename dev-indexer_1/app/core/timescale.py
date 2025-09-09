from __future__ import annotations

import os

try:
        import psycopg2  # type: ignore
except Exception:  # pragma: no cover
        psycopg2 = None  # type: ignore


def ensure_timescale_hypertables() -> None:
        """Ensure Timescale extension, hypertables, and basic policies (idempotent).

        Targets (if present):
            - events(event_time)
            - conversation_events(time)

        Adds compression (7d) and retention policies (30d) when possible.
        Fails silently to avoid blocking app startup.
        """
        if psycopg2 is None:  # pragma: no cover
                return
        dsn = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/rag_db",
        )
        try:
                with psycopg2.connect(dsn, connect_timeout=3) as conn:
                        with conn.cursor() as cur:
                                cur.execute(
                                        """
                                        CREATE EXTENSION IF NOT EXISTS timescaledb;

                                        -- events(event_time)
                                        DO $$
                                        BEGIN
                                            IF to_regclass('public.events') IS NOT NULL THEN
                                                PERFORM create_hypertable('events','event_time', if_not_exists => TRUE);
                                                BEGIN
                                                    EXECUTE 'ALTER TABLE public.events SET (timescaledb.compress)';
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                                BEGIN
                                                    PERFORM add_compression_policy('events', INTERVAL '7 days');
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                                BEGIN
                                                    PERFORM add_retention_policy('events', INTERVAL '30 days');
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                            END IF;
                                        END$$;

                                        -- conversation_events(time)
                                        DO $$
                                        BEGIN
                                            IF to_regclass('public.conversation_events') IS NOT NULL THEN
                                                PERFORM create_hypertable('conversation_events','time', if_not_exists => TRUE);
                                                BEGIN
                                                    EXECUTE 'ALTER TABLE public.conversation_events SET (timescaledb.compress)';
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                                BEGIN
                                                    PERFORM add_compression_policy('conversation_events', INTERVAL '7 days');
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                                BEGIN
                                                    PERFORM add_retention_policy('conversation_events', INTERVAL '30 days');
                                                EXCEPTION WHEN OTHERS THEN NULL;
                                                END;
                                            END IF;
                                        END$$;
                                        """
                                )
                                conn.commit()
        except Exception:
                # non-fatal during startup; diagnostics endpoint can reveal issues
                return
