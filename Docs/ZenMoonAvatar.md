> DEPRECATED: See `Docs/EnhancedZenMoonAvatar.md` for the current avatar component and guidance. This file is kept only for historical reference and may be removed.

# ZenMoonAvatar Component (Deprecated)

## Purpose

This component supersedes the static PNG assets in `src/assets/avatar/` by providing:

- Dynamic facial expressions (eyes, mouths, cheeks)
- Real-time animation based on meditation progress
- Interactive elements with drag/ripple effects
- Contextual emotional responses to app state

## Features

- Animated moon with emotion overlay (cheeks, eyes, mouth)
- Reacts to meditation progress (neutral, happy, joyful, focused)
- Uses animated components from `FaceComponents`
- Drag and drop support
- Aura, ripple, and contextual color effects
- **Replaces**: Static eye/mouth/moon PNG assets with dynamic rendering

## Props (`ZenMoonAvatarProps`)

- `meditationProgress` (number): 0-1, controls emotion overlay
- `enableAura` (boolean): Show animated aura
- `enableInteraction` (boolean): Enable drag/ripple
- ...and more (see code)

## Usage

```tsx
<ZenMoonAvatar meditationProgress={0.7} enableAura enableInteraction />
```

## Related Files

- `FaceComponents.tsx`: Animated facial features
- `hooks/useZenMoon.ts`: Logic hook for state/animation

## Migration from Static Assets

The ZenMoonAvatar component replaces the following static assets:

### Replaced Static Assets

- `src/assets/avatar/eyes/*.png` → Dynamic `<Eye>` component with expression styles
- `src/assets/avatar/mouths/*.png` → Dynamic `<Mouth>` component with expression styles
- `src/assets/avatar/moon/*/` → Programmatic moon with pulse animations

### Benefits of Dynamic Approach

- **Smaller bundle size**: No large PNG files to load
- **Infinite expressions**: Not limited to pre-made asset combinations
- **Smooth transitions**: Animated changes between emotional states
- **Interactive**: Responds to user touch and app state
- **Customizable**: Easy to add new expressions or modify existing ones

### Expression Mapping

- `neutral` → Default calm state
- `happy` → Medium engagement/progress
- `joyful` → High engagement/success
- `focused` → During meditation/concentration activities
