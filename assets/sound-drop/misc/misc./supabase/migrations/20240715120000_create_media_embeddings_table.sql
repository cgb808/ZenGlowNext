-- 1. Ensure you have the pgvector extension enabled
create extension if not exists vector;

-- 2. Create an ENUM type for media for cleaner data
create type public.media_type as enum ('audio', 'image');

-- 3. Create the table to hold media metadata and embeddings
create table public.media (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,

  -- File information from Supabase Storage
  file_path text not null unique, -- e.g., 'meditations/calm_waves.mp3'
  bucket_id text not null,       -- e.g., 'audio-files'
  file_name text,

  -- Our processed metadata
  media_type public.media_type not null,

  -- The vector embedding for similarity search
  -- The size (e.g., 384, 768, 1536) depends on the AI model you choose.
  -- 384 is a common size for smaller, efficient models.
  embedding vector(384),

  -- Indexing status
  status text default 'pending'
);

-- 4. Create standard database indexes for fast lookups
create index idx_media_type on public.media (media_type);
create index idx_media_status on public.media (status);

-- 5. Create a vector index for fast similarity search (IVFFlat)
-- The list_size should be roughly sqrt(number_of_rows) for good performance.
create index idx_media_embedding_ivfflat on public.media using ivfflat (embedding vector_l2_ops) with (lists = 100);

-- 6. Enable Row Level Security (Good Practice)
alter table public.media enable row level security;
-- Note: You'll need to create policies for who can read/write to this table.