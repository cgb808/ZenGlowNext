-- Create the match_audio_clips function for vector similarity search
-- This function respects Row Level Security (RLS) policies

CREATE OR REPLACE FUNCTION public.match_audio_clips(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  title text,
  description text,
  file_url text,
  category text,
  tags text[],
  similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    ac.id,
    ac.title,
    ac.description,
    ac.file_url,
    ac.category,
    ac.tags,
    (ac.embedding <#> query_embedding) * -1 as similarity
  FROM public.audio_clips ac
  WHERE ac.embedding <#> query_embedding < -match_threshold
  ORDER BY ac.embedding <#> query_embedding
  LIMIT match_count;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.match_audio_clips TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_audio_clips TO service_role;
