import { Audio } from 'expo-av';
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { getCachedUri, prefetch } from '../../utils/audio/RemoteAudioCache';
import localSoundMap from './localSoundMap';

// Type definitions for the enhanced sound library
export type SoundName =
  | 'zen_chime'
  | 'zen_bell'
  | 'zen_click_soft'
  | 'zen_whoosh'
  | 'zen_bubble_pop'
  | 'moon_agree_hum'
  | 'moon_disagree_hum'
  | 'moon_maybe_hum'
  | 'moon_happy_giggle'
  | 'moon_focused_breath'
  | 'breathing_in_cue'
  | 'breathing_out_cue'
  | 'meditation_start'
  | 'meditation_end'
  | 'zen_ambient_hum'
  | 'nature_soft_wind'
  | 'zen_om_loop'
  | 'lullaby_custom_zen'
  | 'lullaby_brahms_child';

interface ZenSoundContextType {
  playUI: (name: SoundName) => Promise<void>;
  playLoop: (name: SoundName) => Promise<void>;
  stopLoop: () => Promise<void>;
  playAmbient: () => Promise<void>;
  stopAmbient: () => Promise<void>;
  playCharacterSound: (
    humType: 'agree' | 'disagree' | 'maybe' | 'happy' | 'focused',
  ) => Promise<void>;
  stopAll: () => Promise<void>;
  isAmbientPlaying: boolean;
  setGlobalVolume: (volume: number) => void;
  globalVolume: number;
  isMuted: boolean;
  toggleMute: () => void;
  prewarmSounds: (names: SoundName[]) => Promise<void>;
  setRemoteManifest: (manifest: Partial<Record<SoundName, string>>) => void;
}

// Remote manifest override; hydrate via setRemoteManifest at runtime (e.g., from Supabase/CDN)
const remoteManifestRef: { current: Partial<Record<SoundName, string>> } = { current: {} };

// Sound Library - UI and ZenMoon Character Sounds
type SoundSource = { volume: number; loop?: boolean; file?: any; url?: string };

const soundLibrary: Record<SoundName, SoundSource> = {
  // UI Sounds - instant feedback (these need to be created)
  zen_chime: { volume: 0.8 },
  zen_bell: { volume: 0.7 },
  zen_click_soft: { volume: 0.6 },
  zen_whoosh: { volume: 0.5 },
  zen_bubble_pop: { volume: 0.7 },

  // ZenMoon Character Sounds - personality and engagement (these need to be created)
  moon_agree_hum: { volume: 0.6 },
  moon_disagree_hum: { volume: 0.6 },
  moon_maybe_hum: { volume: 0.6 },
  moon_happy_giggle: { volume: 0.5 },
  moon_focused_breath: { volume: 0.4 },

  // Meditation/Exercise Sounds (these need to be created)
  breathing_in_cue: { volume: 0.5 },
  breathing_out_cue: { volume: 0.5 },
  meditation_start: { volume: 0.6 },
  meditation_end: { volume: 0.6 },

  // Ambient Loops - background atmosphere (these need to be created)
  zen_ambient_hum: { volume: 0.3, loop: true },
  nature_soft_wind: { volume: 0.4, loop: true },
  zen_om_loop: { volume: 0.3, loop: true },

  // Lullabies - existing files (these exist)
  lullaby_custom_zen: { volume: 0.5 },
  lullaby_brahms_child: { volume: 0.5 },
};

// Helper function for fading volume
async function fadeVolume(sound: any, from: number, to: number, duration = 1000) {
  const steps = 20;
  const stepDuration = duration / steps;
  const stepSize = (to - from) / steps;

  for (let i = 0; i <= steps; i++) {
    const progress = i / steps;
    const easedProgress =
      progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress; // Ease-in-out quadratic
    const volume = from + stepSize * easedProgress * steps;
    await sound.setVolumeAsync(Math.max(0, Math.min(1, volume)));
    await new Promise((resolve) => setTimeout(resolve, stepDuration));
  }
}

async function resolveSource(
  src: SoundSource,
): Promise<{ localUri?: string; module?: any; volume: number; loop?: boolean }> {
  if (src.file) return { module: src.file, volume: src.volume, loop: src.loop };
  if (src.url) {
    const localUri = await getCachedUri(src.url);
    return { localUri, volume: src.volume, loop: src.loop };
  }
  // Fallback: nothing resolvable
  return { volume: src.volume, loop: src.loop } as any;
}

// The context definition
const ZenSoundContext = createContext<ZenSoundContextType | null>(null);

export const ZenSoundProvider = ({ children }: { children: React.ReactNode }) => {
  const preloadedSounds = useRef<{ [key: string]: any }>({});
  const activeSound = useRef<any>(null);
  const ambientSound = useRef<any>(null);
  const [isAmbientPlaying, setIsAmbientPlaying] = useState(false);
  const [globalVolume, setGlobalVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);

  const setRemoteManifest = (manifest: Partial<Record<SoundName, string>>) => {
    remoteManifestRef.current = { ...remoteManifestRef.current, ...manifest };
  };

  // Preload sounds on component mount
  useEffect(() => {
    const loadSounds = async () => {
      for (const [key, soundData] of Object.entries(soundLibrary)) {
        if (!(soundData as any).loop) {
          // Only preload non-looping UI sounds
          try {
            const overrideUrl = remoteManifestRef.current[key as SoundName];
            const localModule = localSoundMap[key as SoundName];
            const source: any = localModule
              ? { file: localModule, volume: (soundData as any)?.volume || 1 }
              : overrideUrl
              ? { url: overrideUrl, volume: (soundData as any)?.volume || 1 }
              : (soundData as any);
            const resolved = await resolveSource(source);
            if (resolved.module) {
              const { sound } = await Audio.Sound.createAsync(resolved.module);
              preloadedSounds.current[key] = sound;
            } else if (resolved.localUri) {
              const { sound } = await Audio.Sound.createAsync({ uri: resolved.localUri });
              preloadedSounds.current[key] = sound;
            }
          } catch (e) {
            console.warn(`Could not preload sound: ${key}`, e);
          }
        }
      }
    };

    loadSounds();

    // Cleanup function
    return () => {
      Object.values(preloadedSounds.current).forEach((sound: any) => sound?.unloadAsync?.());
      if (activeSound.current) activeSound.current.unloadAsync();
      if (ambientSound.current) ambientSound.current.unloadAsync();
    };
  }, []);

  // UI sound player - instant feedback
  const playUI = async (name: SoundName) => {
    if (isMuted) return;

    const base = soundLibrary[name] as any;
    if (!base || base.loop) {
      console.warn(`UI Sound "${name}" not found or is a loop.`);
      return;
    }

    try {
      let sound = preloadedSounds.current[name];
      const overrideUrl = remoteManifestRef.current[name];
      const localModule = localSoundMap[name];
      if (!sound) {
        const source: any = localModule
          ? { file: localModule, volume: base.volume || 1 }
          : overrideUrl
          ? { url: overrideUrl, volume: base.volume || 1 }
          : base;
        const resolved = await resolveSource(source);
        if (resolved.module) {
          const created = await Audio.Sound.createAsync(resolved.module);
          sound = created.sound;
        } else if (resolved.localUri) {
          const created = await Audio.Sound.createAsync({ uri: resolved.localUri });
          sound = created.sound;
        }
        if (sound) preloadedSounds.current[name] = sound;
      }
      if (sound) {
        await sound.setVolumeAsync(((base.volume || 1.0) as number) * globalVolume);
        await sound.replayAsync();
      }
    } catch (e) {
      console.warn(`Error playing UI sound "${name}":`, e);
    }
  };

  // Loop sound player - for ambient/background sounds
  const playLoop = async (name: SoundName) => {
    if (isMuted) return;

    const soundData = soundLibrary[name] as any;
    if (!soundData || !soundData.loop) {
      console.warn(`Loop sound "${name}" not found or not configured as loop.`);
      return;
    }

    try {
      if (activeSound.current) await activeSound.current.unloadAsync();
      const overrideUrl = remoteManifestRef.current[name];
      const localModule = localSoundMap[name];
      const source: any = localModule
        ? { file: localModule, volume: soundData.volume || 1, loop: true }
        : overrideUrl
        ? { url: overrideUrl, volume: soundData.volume || 1, loop: true }
        : soundData;
      const resolved = await resolveSource(source);
      let created;
      if (resolved.module) {
        created = await Audio.Sound.createAsync(resolved.module, {
          shouldPlay: true,
          isLooping: true,
          volume: (soundData.volume || 1.0) * globalVolume,
        });
      } else if (resolved.localUri) {
        created = await Audio.Sound.createAsync(
          { uri: resolved.localUri },
          {
            shouldPlay: true,
            isLooping: true,
            volume: (soundData.volume || 1.0) * globalVolume,
          },
        );
      }
      const { sound } = created!;
      activeSound.current = sound;
    } catch (e) {
      console.warn(`Error playing loop sound "${name}":`, e);
    }
  };

  const stopLoop = async () => {
    try {
      if (activeSound.current) {
        await activeSound.current.stopAsync();
        await activeSound.current.unloadAsync();
        activeSound.current = null;
      }
    } catch (e) {
      console.warn('Error stopping loop:', e);
    }
  };

  // Character sound player - ZenMoon personality sounds
  const playCharacterSound = async (
    humType: 'agree' | 'disagree' | 'maybe' | 'happy' | 'focused',
  ) => {
    const soundMap = {
      agree: 'moon_agree_hum',
      disagree: 'moon_disagree_hum',
      maybe: 'moon_maybe_hum',
      happy: 'moon_happy_giggle',
      focused: 'moon_focused_breath',
    };

    const soundName = soundMap[humType] as SoundName;
    await playUI(soundName);
  };

  // Ambient functions
  const playAmbient = async () => {
    if (isAmbientPlaying || isMuted) return;
    try {
      const srcBase = soundLibrary.zen_ambient_hum as any;
      const overrideUrl = remoteManifestRef.current['zen_ambient_hum'];
      const localModule = localSoundMap['zen_ambient_hum'];
      const src = localModule
        ? { file: localModule, volume: srcBase.volume || 1, loop: true }
        : overrideUrl
        ? { url: overrideUrl, volume: srcBase.volume || 1, loop: true }
        : srcBase;
      const resolved = await resolveSource(src as any);
      let created;
      if (resolved.module) {
        created = await Audio.Sound.createAsync(resolved.module, { isLooping: true, volume: 0 });
      } else if (resolved.localUri) {
        created = await Audio.Sound.createAsync(
          { uri: resolved.localUri },
          { isLooping: true, volume: 0 },
        );
      }
      const { sound } = created!;
      ambientSound.current = sound;
      await sound.playAsync();
      await fadeVolume(sound, 0, (srcBase.volume || 1) * globalVolume, 1200);
      setIsAmbientPlaying(true);
    } catch (e) {
      console.warn('Ambient load error:', e);
    }
  };

  const stopAmbient = async () => {
    if (!isAmbientPlaying) return;
    try {
      if (ambientSound.current) {
        await fadeVolume(
          ambientSound.current,
          soundLibrary.zen_ambient_hum.volume * globalVolume,
          0,
          800,
        );
        await ambientSound.current.stopAsync();
        await ambientSound.current.unloadAsync();
        ambientSound.current = null;
      }
      setIsAmbientPlaying(false);
    } catch (e) {
      console.warn('Stop ambient error:', e);
    }
  };

  const stopAll = async () => {
    await stopLoop();
    await stopAmbient();
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (!isMuted) {
      stopAll(); // Stop all sounds when muting
    }
  };

  const prewarmSounds = async (names: SoundName[]) => {
    if (isMuted) return;
    const urls: string[] = [];
    for (const n of names) {
      const remote = remoteManifestRef.current[n];
      if (remote) urls.push(remote);
    }
    if (urls.length) await prefetch(urls);

    // Preload non-looping sounds for faster UI feedback
    for (const n of names) {
      const src = localSoundMap[n]
        ? { file: localSoundMap[n], volume: (soundLibrary[n] as any)?.volume || 1 }
        : remoteManifestRef.current[n]
        ? { url: remoteManifestRef.current[n]!, volume: (soundLibrary[n] as any)?.volume || 1 }
        : (soundLibrary[n] as any);
      if (!src) continue;
      const resolved = await resolveSource(src);
      if (resolved.module) {
        // existing local module path
        if (!preloadedSounds.current[n]) {
          try {
            const { sound } = await Audio.Sound.createAsync(resolved.module);
            preloadedSounds.current[n] = sound;
          } catch {}
        }
      } else if (resolved.localUri) {
        try {
          const { sound } = await Audio.Sound.createAsync({ uri: resolved.localUri });
          preloadedSounds.current[n] = sound;
        } catch {}
      }
    }
  };

  // The context value provides all functionality
  const value: ZenSoundContextType = {
    playUI,
    playLoop,
    stopLoop,
    playAmbient,
    stopAmbient,
    playCharacterSound,
    stopAll,
    isAmbientPlaying,
    setGlobalVolume,
    globalVolume,
    isMuted,
    toggleMute,
    prewarmSounds,
    setRemoteManifest,
  };

  return <ZenSoundContext.Provider value={value}>{children}</ZenSoundContext.Provider>;
};

// The hook for consuming the context
export const useZenSound = () => {
  const context = useContext(ZenSoundContext);
  if (!context) throw new Error('useZenSound must be used within ZenSoundProvider');
  return context;
};
