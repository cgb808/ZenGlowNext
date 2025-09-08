# EnhancedZenMoonAvatar

A modern, animated moon avatar with dynamic aura, expressive eyes/mouth, and Reanimated-driven motion. This supersedes the older ZenMoonAvatar docs and is the recommended component for the floating companion and future UI.

## Props

- mood: "calm" | "joyful" | "curious" | "focused" | "playful" | "sleepy" (default: "calm")
- size: number (default: 120)
- zenScore: number (default: 75) — reserved for future dynamic styling
- behavior: "idle" | "active" | "sleep" (default: "idle")

## Integration

Use with the floating companion:

```tsx
import { EnhancedZenMoonAvatar } from '../components/ZenMoon/EnhancedZenMoonAvatar';

<EnhancedZenMoonAvatar mood={mood} size={80} behavior="idle" />;
```

The companion handles gaze, drag, and layout; the avatar focuses on visuals.

## Implementation Notes

- Built with react-native-reanimated shared values for transforms (scale/scaleY)
- Aura uses withRepeat(withSequence(withTiming(...))) for gentle pulse
- DramaticEye/DramaticMouth use shared values to avoid transform type errors
- Color palettes are mood-keyed and can be extended

## Related Files

- components/ZenMoon/EnhancedZenMoonAvatar.tsx
- components/Companion/ZenGlowCompanion.tsx
- components/ZenMoon/FaceComponents.tsx (shared ideas/legacy)

## Migration Guidance

- Replace previous usage of `ZenMoonAvatar` with `EnhancedZenMoonAvatar`.
- The old Docs/ZenMoonAvatar.md is deprecated; this file is the source of truth.
