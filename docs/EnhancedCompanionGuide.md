# Enhanced ZenGlow Companion Documentation

## Overview

The Enhanced ZenGlow Companion is an intelligent AI assistant that provides context-aware guidance and support throughout the ZenGlow app experience. It features real-time decision making, smooth animations, voice integration, and comprehensive accessibility support.

## Architecture

### Core Components

1. **useCompanionAI Hook** - The brain of the companion system
2. **CompanionBehaviorEngine** - Intelligent decision-making logic
3. **CompanionAnimations** - Advanced animation system
4. **UIElementContext** - Enhanced UI awareness
5. **CompanionAccessibility** - Accessibility features

### System Flow

```
User Interaction → UIElementContext → useCompanionAI → BehaviorEngine → CompanionAnimations → Visual Response
                                                    ↓
                                                Voice Response
                                                    ↓
                                            Accessibility Announcements
```

## Quick Start

### Basic Integration

The companion is automatically integrated in the root layout, but you can register UI elements for awareness:

```typescript
import { useUIElements } from '../contexts/UIElementContext';

const MyComponent = () => {
  const { registerElement } = useUIElements();

  const handleLayout = (event) => {
    registerElement('my-button', {
      ...event.nativeEvent.layout,
      type: 'button',
      priority: 'high',
      interactive: true,
    });
  };

  return (
    <TouchableOpacity onLayout={handleLayout}>
      <Text>My Button</Text>
    </TouchableOpacity>
  );
};
```

### Advanced Usage

For more control over companion behavior:

```typescript
import { useCompanionAI } from '../hooks/useCompanionAI';
import { companionAccessibility } from '../utils/CompanionAccessibility';

const MyScreen = () => {
  const { 
    companionState, 
    updateCurrentScreen, 
    updateUserContext,
    speak 
  } = useCompanionAI('family-id', 'child-id');

  useEffect(() => {
    // Notify companion of screen change
    updateCurrentScreen('my-screen');
    
    // Provide accessibility context
    companionAccessibility.provideContextualHelp({
      currentScreen: 'my-screen',
      lastUserAction: 'navigation',
      timeOfDay: 'morning',
      sessionDuration: 0,
    });
  }, []);

  const handleSpecialAction = async () => {
    // Speak to user
    await speak("Great job! You're making progress!");
    
    // Update context
    updateUserContext({ 
      lastUserAction: 'tap',
      userMood: 'excited' 
    });
  };

  return (
    // Your screen content
  );
};
```

## Features

### 🧠 AI-Powered Intelligence

#### Decision Making
The companion uses the `CompanionBehaviorEngine` to make intelligent decisions based on:
- Current screen context
- User interaction patterns
- Time of day and session duration
- UI element priority and types
- User mood and energy levels

#### Supported Actions
- **lookAt**: Gaze at specific UI elements
- **wave**: Friendly greeting gesture
- **nod**: Agreement or acknowledgment
- **celebrate**: Achievement celebration
- **point**: Direct attention to elements
- **nudge**: Gentle attention seeking
- **speak**: Voice announcements
- **hide**: Become less obtrusive
- **awaken**: Return to active state

#### Context Triggers
- `user_tap`: User touches screen
- `idle`: User inactive for period
- `screen_change`: Navigation to new screen
- `mood_change`: User mood detection
- `timer`: Time-based interventions
- `element_appeared`: New UI elements

### 🎨 Animation System

#### Action Animations
Each action has custom animations with personality-based intensity:
- Celebration bouncing and rotation
- Wave gestures with scale effects
- Nodding with vertical motion
- Pointing with directional emphasis

#### Mood-Based Floating
Continuous floating animation that changes based on:
- **Excited**: Energetic, fast floating (12px amplitude)
- **Calm**: Gentle, slow floating (4px amplitude)
- **Sleepy**: Minimal, very slow floating (2px amplitude)
- **Playful**: Irregular, bouncy patterns

#### Performance Features
- React Native Reanimated 3 optimized
- Worklet-based animations for 60fps
- Energy-aware animation intensity
- Reduced motion accessibility support

### 🗣️ Voice Integration

#### Text-to-Speech Features
```typescript
// Basic speaking
await speak("Hello! I'm here to help!");

// With custom settings
await speak("Take a deep breath", {
  rate: 0.7,    // Slower speech
  pitch: 1.2,   // Higher pitch
  language: 'en-US'
});
```

#### Voice Settings
- Rate control (0.1-1.0)
- Pitch adjustment (0.5-2.0)
- Language selection
- Voice customization
- Fallback to console logging

#### Context-Appropriate Messages
- Welcome messages for new users
- Encouragement during activities
- Celebration for achievements
- Guidance for navigation
- Support during difficult moments

### 🧩 Enhanced UI Awareness

#### Element Registration
```typescript
registerElement('important-button', {
  x, y, width, height,
  type: 'button',           // button, card, input, notification, etc.
  priority: 'high',         // low, medium, high, critical
  interactive: true,        // Can be interacted with
  accessible: true,         // Supports accessibility
  metadata: {
    title: 'Start Meditation',
    description: 'Main action button'
  }
});
```

#### Smart Detection
- **Priority-based attention**: High priority elements get more focus
- **Type-aware responses**: Different behaviors for buttons vs cards
- **Proximity detection**: Find nearest elements to companion
- **Interactive filtering**: Focus on actionable elements

#### Context Functions
```typescript
// Get elements in area
const nearbyElements = getElementsInArea(x, y, radius);

// Get high priority elements
const important = getHighPriorityElements();

// Get interactive elements
const clickable = getInteractiveElements();
```

### ♿ Accessibility Features

#### Screen Reader Support
```typescript
// Announce to screen readers
companionAccessibility.announceForScreenReader(
  "Meditation session started", 
  'assertive'  // or 'polite'
);

// Action announcements
companionAccessibility.announceAction(action);
```

#### Touch Guidance
```typescript
// Provide spatial guidance
companionAccessibility.provideTouchGuidance(
  'Settings Button', 
  { x: 100, y: 200 }
);
```

#### Accessibility Detection
- Automatic screen reader detection
- Reduced motion preference respect
- High contrast mode support
- Large text adaptation

### 🎛️ Personalization

#### Personality Traits
```typescript
const personality = {
  responsiveness: 0.7,  // How quickly to react (0-1)
  playfulness: 0.6,     // Tendency for fun interactions (0-1)
  helpfulness: 0.8,     // Tendency to guide/assist (0-1)
  expressiveness: 0.7,  // Animation intensity (0-1)
  chattiness: 0.5,      // Frequency of speaking (0-1)
};

// Update personality
setPersonality({ playfulness: 0.9 });
```

## API Reference

### useCompanionAI Hook

```typescript
const {
  // State
  companionState,     // Current companion state
  userContext,        // User context tracking
  personality,        // Personality settings
  voiceSettings,      // TTS configuration
  
  // Actions
  performAction,      // Execute companion action
  speak,             // Text-to-speech
  decideNextAction,  // AI decision making
  
  // Context Updates
  updateUserContext,    // Update user state
  updateCurrentScreen,  // Change screen context
  updatePosition,       // Update companion position
  
  // Settings
  setPersonality,       // Modify personality
  setVoiceSettings,     // Configure TTS
  
  // Utilities
  shouldIntervene,      // Check if help needed
  getCurrentTimeOfDay,  // Get time context
} = useCompanionAI(familyId, childId);
```

## Best Practices

### Performance
1. **Limit element registration**: Only register important UI elements
2. **Use priorities wisely**: Reserve 'critical' for truly important elements
3. **Clean up elements**: Unregister elements when components unmount
4. **Respect reduced motion**: Check accessibility preferences

### User Experience
1. **Context awareness**: Update screen context on navigation
2. **Meaningful interactions**: Register interactive elements properly
3. **Accessibility first**: Always provide accessibility labels
4. **Personality consistency**: Maintain personality settings across sessions

### Development
1. **Type safety**: Use provided TypeScript types
2. **Error handling**: Wrap TTS calls in try-catch
3. **Testing**: Test with screen readers enabled
4. **Performance monitoring**: Watch animation performance

## Troubleshooting

### Common Issues

#### TTS Not Working
```typescript
// Check TTS availability
try {
  await speak("Test message");
} catch (error) {
  console.log("TTS fallback:", error);
  // Fallback to visual feedback
}
```

#### Animations Too Intense
```typescript
// Check reduced motion preference
if (companionAccessibility.shouldReduceAnimations()) {
  // Use minimal animations
  setPersonality({ expressiveness: 0.2 });
}
```

#### Companion Not Responding
```typescript
// Check if companion state is updating
console.log('Companion state:', companionState);

// Verify element registration
console.log('Registered elements:', elements);

// Check decision context
const action = decideNextAction(context);
console.log('Next action:', action);
```

## Migration Guide

### From Previous Version

If upgrading from the basic companion:

1. **Imports remain the same** - Backward compatibility maintained
2. **Additional features available** - Access via enhanced hook
3. **Performance improved** - Better animation system
4. **New registrations** - Add element types and priorities

### Breaking Changes
- None - Full backward compatibility maintained

The Enhanced ZenGlow Companion represents a significant upgrade in AI-powered user assistance, providing intelligent, accessible, and delightful interactions throughout the app experience.