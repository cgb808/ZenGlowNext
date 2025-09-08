# ZenSoundProvider - Enhanced for ZenMoon Integration

A scalable, context-based sound manager for the ZenGlow app, specifically designed to work seamlessly with the ZenMoon avatar for maximum child engagement.

## 🌟 **Key Features for Child Engagement**

- **Character-driven sounds**: ZenMoon responds with personality sounds (giggles, hums, breaths)
- **Progressive audio feedback**: Sounds change based on meditation progress and expressions
- **Global sound triggers**: ZenMoon animations automatically trigger appropriate sounds
- **Child-safe volume controls**: Built-in volume limits and mute functionality
- **Seamless UI integration**: Every interaction has instant audio feedback

## Core Functionality

- Centralized `soundLibrary` for all app sounds
- Preloads non-looping UI sounds for instant playback
- `playUI(name)` for instant UI feedback sounds
- `playCharacterSound(humType)` for ZenMoon personality responses
- `playLoop(name)` and `stopLoop()` for ambient sounds
- `playAmbient()` and `stopAmbient()` for meditation backgrounds
- Volume and mute controls: `setGlobalVolume`, `toggleMute`
- `stopAll()` to stop all active sounds
- Auto-cleanup on unmount `useZenSound` hook for easy access in any component

## Usage with ZenMoon Integration

Wrap your app with the provider:

```tsx
<ZenSoundProvider>
  <ZenMoonFaceFloating 
    expression="happy" 
    meditationProgress={0.7}
    isActive={true}
    enableSound={true}
  />
  {/* ...your app... */}
</ZenSoundProvider>
```

In any child component:

```tsx
import { useZenSound, SoundName } from './ZenSoundProviderEnhanced';
const { 
  playUI, 
  playCharacterSound, 
  playLoop, 
  stopLoop, 
  playAmbient, 
  stopAmbient, 
  setGlobalVolume, 
  toggleMute, 
  stopAll,
  isMuted, 
  globalVolume, 
  isAmbientPlaying 
} = useZenSound();

// Play UI feedback sound
playUI('zen_chime');

// ZenMoon character sounds based on interaction
playCharacterSound('agree');  // Happy hum
playCharacterSound('happy');  // Giggle
playCharacterSound('focused'); // Breathing sound

// Background meditation sounds
playLoop('zen_ambient_hum');
playAmbient(); // Special fade-in ambient

// Volume controls
setGlobalVolume(0.7); // 0.0 - 1.0
toggleMute(); // Child-safe mute toggle
```

## ZenMoon Character Sound Integration

The `playCharacterSound()` function provides personality-driven audio:

```tsx
// In meditation/exercise components
const handleMeditationProgress = (progress) => {
  if (progress > 0.8) {
    playCharacterSound('happy'); // Triggers moon_happy_giggle
  } else if (progress > 0.5) {
    playCharacterSound('agree'); // Triggers moon_agree_hum  
  }
};

// Global triggers (automatically called by ZenMoon animations)
global.zenSound(); // Plays appropriate character sound
global.zenPulse(); // Triggers visual + audio feedback
```

## Sound Library Example

```ts
const soundLibrary = {
  // UI Sounds (preloaded for instant playback)
  mmm: { file: require('../assets/sounds/ui/zen_mmm.mp3') },
  chime: { file: require('../assets/sounds/ui/zen_chime.mp3'), volume: 0.6 },
  bell: { file: require('../assets/sounds/ui/zen_bell.mp3'), volume: 0.7 },
  // Looping Sounds (loaded on demand)
  wind: { file: require('../assets/sounds/ambient/zen_wind.mp3'), volume: 0.3, loop: true },
  hum: { file: require('../assets/sounds/ambient/zen_hum_loop.mp3'), volume: 0.4, loop: true },
};
```

## Type Definitions

```ts
export type SoundName = keyof typeof soundLibrary;

interface ZenSoundContextType {
  playUI: (name: SoundName) => void;
  playLoop: (name: SoundName) => void;
  stopLoop: () => void;
  playAmbient: () => void;
  stopAmbient: () => void;
  playMultipleUI: (names: SoundName[]) => void;
  stopAll: () => void;

  // State
  currentLoop: SoundName | null;
  isAmbientPlaying: boolean;
  isMuted: boolean;
  globalVolume: number;

  // Volume and mute controls
  setGlobalVolume: (volume: number) => void;
  toggleMute: () => void;
  setMute: (muted: boolean) => void;
}
```

## Context Value

- `playUI(name: SoundName)` — Play a preloaded UI sound by name
- `playMultipleUI([name, ...])` — Play multiple UI sounds at once (sound mixing)
- `playLoop(name: SoundName)` — Play a looping/ambient sound by name
- `stopLoop()` — Stop any looping/active sound
- `playAmbient()` — Start ambient hum (with fade in)
- `stopAmbient()` — Stop ambient hum (with fade out)
- `stopAll()` — Stop all active sounds
- `setGlobalVolume(volume: number)` — Set global volume (0.0 - 1.0)
- `toggleMute()` — Toggle mute on/off
- `setMute(muted: boolean)` — Explicitly set mute state
- `currentLoop` — Name of the currently playing loop, or null
- `isAmbientPlaying` — Boolean, true if ambient is playing
- `isMuted` — Boolean, true if muted
- `globalVolume` — Current global volume (0.0 - 1.0)

## Related

- [Expo AV documentation](https://docs.expo.dev/versions/latest/sdk/av/)
- Used by: all interactive and feedback components in ZenGlow
- See also: [ZenMoonAvatar.md], [FaceComponents.md], [dependencies.md]
