# Environment setup

This app uses a simple, consistent env flow:

- Client (Expo app): values come from app.config.ts → extra → Constants.expoConfig.extra
- Server/Node scripts: load .env with dotenv automatically in each script

## Required variables

Create a .env at the repo root based on .env.example:

- SUPABASE_URL: Your Supabase project URL, e.g. https://xyz.supabase.co
- SUPABASE_ANON_KEY: Your Supabase public (anon) key
- AUDIO_CACHE_TTL_MS (optional): TTL for cached audio files (ms)

## How values reach the app

- app.config.ts imports dotenv/config and merges values into extra:
  - extra.supabaseUrl
  - extra.supabaseAnonKey
- Use utils/env.ts in-app to read them safely.

Never include service role keys or secrets in client extras.

## Related docs

- Docs/AUDIO_GUIDE.md – cloud audio, caching, prewarm, and manifests.
