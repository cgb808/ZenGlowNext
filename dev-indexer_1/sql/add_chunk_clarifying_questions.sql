-- Migration: add chunk_clarifying_questions table
-- Idempotent: checks existence before creating
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='chunk_clarifying_questions'
    ) THEN
        CREATE TABLE public.chunk_clarifying_questions (
            id BIGSERIAL PRIMARY KEY,
            chunk_id BIGINT NOT NULL REFERENCES public.doc_embeddings(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT,
            status TEXT NOT NULL DEFAULT 'open', -- open|answered|dismissed
            priority SMALLINT DEFAULT 0,
            metadata JSONB,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_ccq_chunk_id ON public.chunk_clarifying_questions(chunk_id);
        CREATE INDEX IF NOT EXISTS idx_ccq_status ON public.chunk_clarifying_questions(status);
    END IF;
END $$;

-- Trigger to keep updated_at fresh
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'tr_ccq_updated_at'
    ) THEN
        CREATE OR REPLACE FUNCTION public.set_updated_at_ccq() RETURNS trigger AS $CCQ$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $CCQ$ LANGUAGE plpgsql;
        CREATE TRIGGER tr_ccq_updated_at
            BEFORE UPDATE ON public.chunk_clarifying_questions
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_ccq();
    END IF;
END $$;