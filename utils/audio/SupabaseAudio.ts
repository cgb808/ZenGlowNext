type Manifest = Record<string, string>;

export interface FetchManifestOptions {
  supabaseUrl: string; // e.g., https://xyzcompany.supabase.co
  anonKey: string; // SUPABASE_ANON_KEY (do not ship service role key to clients)
  view: string; // logical view/screen name: 'child-dashboard', 'parent-dashboard', etc.
  profileId?: string; // optional child/user profile scope
  signal?: AbortSignal;
}

/**
 * Fetch a sound manifest for a given view from a Supabase Edge Function.
 * Expected response: { manifest: { [soundName]: "https://cdn/.../file.mp3" } }
 * The edge function should enforce RLS/authorization and return signed URLs if needed.
 */
export async function fetchSoundManifest(opts: FetchManifestOptions): Promise<Manifest> {
  const { supabaseUrl, anonKey, view, profileId, signal } = opts;
  const url = `${supabaseUrl}/functions/v1/match-audio-clips`;
  const res = await fetch(
    `${url}?view=${encodeURIComponent(view)}${
      profileId ? `&profile=${encodeURIComponent(profileId)}` : ''
    }`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${anonKey}`,
        apikey: anonKey,
      },
      signal,
    },
  );
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`fetchSoundManifest failed: ${res.status} ${text}`);
  }
  const json = await res.json().catch(() => ({}));
  return (json?.manifest ?? {}) as Manifest;
}
