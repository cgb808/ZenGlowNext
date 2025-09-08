# EnhancedZenMoonAvatar Inactivity Logic and Sparkle Effects

## Overview

The EnhancedZenMoonAvatar now includes advanced inactivity detection, suggestion animations, and sparkle effects to create engaging interactions for children. When a user is inactive for a configurable period, the moon will suggest buttons by flying to them, playing sounds, and showing sparkle effects.

## Features

### 🔍 Inactivity Detection
- Configurable timeout (default: 7 seconds)
- Automatic reset on user interaction
- Can be enabled/disabled via props

### 🌙 Moon Animation Sequence
1. **Flight**: Moon flies smoothly to suggested button location
2. **Looking**: Eyes rotate to look at button, then around
3. **Return**: Moon returns to original position after interaction or timeout

### 🔊 Sound Integration
- Plays "hmmm" sound effect during suggestion phase
- Uses existing ZenSoundProvider infrastructure
- Graceful fallback if sounds fail to load

### ✨ Sparkle Effects
- Customizable sparkle count, color, size, and duration
- SVG-based star shapes with smooth animations
- Appear around suggested buttons during suggestion phase

### 🎛️ Configuration Options
- **Inactivity timeout**: 5-10 seconds (or custom)
- **Sparkle appearance**: Count, color, size, animation duration
- **Button targeting**: Pass refs of buttons to suggest
- **Interaction callbacks**: Get notified when user interacts

## Usage

### Basic Implementation

```tsx
import React, { useRef } from 'react';
import { View, TouchableOpacity, Text } from 'react-native';
import { EnhancedZenMoonAvatar } from '../components/ZenMoon/EnhancedZenMoonAvatar';

export const MyComponent = () => {
  const buttonRef1 = useRef<View>(null);
  const buttonRef2 = useRef<View>(null);
  const avatarRef = useRef<{ handleUserInteraction: () => void }>(null);

  const handleButtonPress = () => {
    // Notify avatar of user interaction
    avatarRef.current?.handleUserInteraction();
  };

  return (
    <View>
      <EnhancedZenMoonAvatar
        ref={avatarRef}
        mood="curious"
        size={120}
        suggestedButtonRefs={[buttonRef1, buttonRef2]}
      />
      
      <TouchableOpacity ref={buttonRef1} onPress={handleButtonPress}>
        <Text>Button 1</Text>
      </TouchableOpacity>
      
      <TouchableOpacity ref={buttonRef2} onPress={handleButtonPress}>
        <Text>Button 2</Text>
      </TouchableOpacity>
    </View>
  );
};
```

### Advanced Configuration

```tsx
<EnhancedZenMoonAvatar
  mood="joyful"
  size={100}
  suggestedButtonRefs={buttonRefs}
  sparkleConfig={{
    count: 6,                 // Number of sparkles
    color: '#FFD700',         // Gold sparkles
    duration: 1500,           // 1.5 second animation
    repeat: true,             // Continuous sparkles
  }}
  inactivityConfig={{
    timeout: 5000,            // 5 second timeout
    enabled: true,            // Enable inactivity detection
  }}
  onUserInteraction={() => {
    console.log('User is active again!');
  }}
/>
```

## Props

### EnhancedZenMoonAvatarProps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `mood` | `MoodType` | `'calm'` | Moon's emotional state |
| `size` | `number` | `120` | Size of the moon avatar |
| `suggestedButtonRefs` | `RefObject<View>[]` | `[]` | Refs to buttons for suggestions |
| `sparkleConfig` | `SparkleConfig` | `{}` | Sparkle effect configuration |
| `inactivityConfig` | `InactivityConfig` | `{}` | Inactivity detection settings |
| `onUserInteraction` | `() => void` | `undefined` | Callback when user interacts |

### SparkleConfig

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `count` | `number` | `4` | Number of sparkles to show |
| `color` | `string` | `colors.accent` | Sparkle color |
| `duration` | `number` | `1500` | Animation duration (ms) |
| `repeat` | `boolean` | `true` | Whether to repeat animation |

### InactivityConfig

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `timeout` | `number` | `7000` | Inactivity timeout (ms) |
| `enabled` | `boolean` | `true` | Enable inactivity detection |

## Sparkle Component

The `Sparkle` component is a reusable SVG-based star animation that can be used independently.

### SparkleProps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `color` | `string` | `'#FFD700'` | Sparkle color |
| `size` | `number` | `12` | Sparkle size |
| `duration` | `number` | `1000` | Animation duration |
| `delay` | `number` | `0` | Animation delay |
| `repeat` | `boolean` | `true` | Repeat animation |
| `offsetX` | `number` | `0` | Horizontal offset |
| `offsetY` | `number` | `0` | Vertical offset |

### Standalone Usage

```tsx
import { Sparkle } from '../components/ZenMoon/Sparkle';

<Sparkle
  color="#FF6B6B"
  size={16}
  duration={2000}
  delay={500}
  repeat={false}
  offsetX={20}
  offsetY={-10}
/>
```

## Integration with Parent Components

### Imperative API

The EnhancedZenMoonAvatar provides an imperative API through refs:

```tsx
const avatarRef = useRef<{ handleUserInteraction: () => void }>(null);

// Call when user interacts with your app
const onAnyUserAction = () => {
  avatarRef.current?.handleUserInteraction();
};
```

### Button Reference Setup

Pass refs of interactive elements you want the moon to suggest:

```tsx
const breatheButtonRef = useRef<View>(null);
const meditateButtonRef = useRef<View>(null);

<EnhancedZenMoonAvatar
  suggestedButtonRefs={[breatheButtonRef, meditateButtonRef]}
/>

<TouchableOpacity ref={breatheButtonRef}>
  <Text>Breathe</Text>
</TouchableOpacity>
```

## Animation Sequence Details

### 1. Inactivity Detection
- Timer starts when component mounts or after user interaction
- Resets whenever `handleUserInteraction()` is called
- Configurable timeout period

### 2. Suggestion Phase
- Random button selection from provided refs
- Moon flies to calculated position near button
- "Hmmm" sound plays via ZenSoundProvider
- Eyes animate to look at button, then around

### 3. Sparkle Effects
- Sparkles appear around suggested button area
- Configurable count, color, size, and timing
- SVG-based stars with fade/pulse animations
- Random positioning within defined area

### 4. Return Phase
- Moon returns to center position after 4 seconds
- Immediate return if user interacts during suggestion
- All animations reset to default state

## Sound Integration

The component integrates with the existing ZenSoundProvider:

```tsx
import { useZenSound } from '../Audio/ZenSoundProvider';

// Uses 'maybe' character sound for "hmmm" effect
await playCharacterSound('maybe');
```

Ensure your app is wrapped with ZenSoundProvider for sound functionality.

## Performance Considerations

- Uses react-native-reanimated for smooth 60fps animations
- Sparkles use shared values for optimal performance
- Sound loading is handled by ZenSoundProvider caching
- Animation cleanup on component unmount

## Accessibility

- Sound effects can be muted via ZenSoundProvider
- Visual animations remain functional without sound
- Component maintains original accessibility features

## Example Demo

See `examples/ZenMoonInactivityDemo.tsx` for a complete working example showcasing all features.

## Migration from Previous Version

The new props are optional, so existing implementations will continue to work unchanged:

```tsx
// Old usage - still works
<EnhancedZenMoonAvatar mood="calm" size={120} />

// New usage - with inactivity features
<EnhancedZenMoonAvatar 
  mood="calm" 
  size={120}
  suggestedButtonRefs={buttonRefs}
  inactivityConfig={{ timeout: 5000 }}
/>
```

## Troubleshooting

### Sparkles Not Appearing
- Ensure `suggestedButtonRefs` contains valid refs
- Check that inactivity timeout is being reached
- Verify ZenSoundProvider is wrapping the component

### Sounds Not Playing
- Confirm ZenSoundProvider is properly configured
- Check if app is muted via provider settings
- Verify sound files exist (handled by provider)

### Animation Performance Issues
- Reduce sparkle count in `sparkleConfig.count`
- Increase animation duration for smoother motion
- Ensure react-native-reanimated is properly installed

## Related Components

- `ZenSoundProvider` - Audio system integration
- `Sparkle` - Reusable sparkle effect component
- Original `EnhancedZenMoonAvatar` - Base moon avatar functionality