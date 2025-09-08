import { useEffect } from 'react';
import { SoundName, useZenSound } from '../components/Audio/ZenSoundProvider';

/**
 * Prewarm sounds for a specific view to avoid first-tap latency.
 * Usage:
 *   useWarmSounds(['zen_click_soft', 'zen_chime']);
 */
export function useWarmSounds(names: SoundName[]) {
  const { prewarmSounds } = useZenSound();
  useEffect(() => {
    prewarmSounds(names).catch(() => {});
  }, [prewarmSounds, names.join(',')]);
}
