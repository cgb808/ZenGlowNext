import { useEffect } from 'react';
import { fetchSoundManifest } from '../../utils/audio/SupabaseAudio';
import { getSupabaseClientEnv } from '../../utils/env';
import { useZenSound } from './ZenSoundProvider';

export function AudioBootstrapper() {
  const { setRemoteManifest, prewarmSounds } = useZenSound();
  useEffect(() => {
    const { supabaseUrl, supabaseAnonKey } = getSupabaseClientEnv();
    if (!supabaseUrl || !supabaseAnonKey) {
      console.warn('Missing Supabase env. Skipping audio manifest bootstrap.');
      return;
    }
    let aborted = false;
    const ctrl = new AbortController();
    (async () => {
      try {
        const manifest = await fetchSoundManifest({
          supabaseUrl,
          anonKey: supabaseAnonKey,
          view: 'root',
          signal: ctrl.signal,
        });
        if (aborted) return;
        setRemoteManifest(manifest as any);
        await prewarmSounds([
          'zen_click_soft',
          'zen_chime',
          'zen_bubble_pop',
          'zen_ambient_hum',
        ] as any);
      } catch (e) {
        if (!aborted) console.warn('Audio manifest bootstrap failed:', e);
      }
    })();
    return () => {
      aborted = true;
      ctrl.abort();
    };
  }, [setRemoteManifest, prewarmSounds]);
  return null;
}
