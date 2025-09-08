## Hermes enablement and debugging

- Enabled Hermes in `app.json`:
  - `ios.jsEngine = "hermes"`
  - `android.jsEngine = "hermes"`
- VS Code launch configs added in `.vscode/launch.json` to attach to Hermes on Android/iOS.
- Run the app, then use "Run and Debug" -> "Attach to Hermes (Android)".

# ZenGlow Development Snippets & Patterns

## 🧩 RECOMMENDED SNIPPETS TO FEED CLAUDE

### Core Snippet Library

| 🔤 Abbr | 💥 Expansion                             | 📍 When to Use                                                            |
| ------- | ---------------------------------------- | ------------------------------------------------------------------------- |
| `rafce` | React Arrow Function Component + export  | New screens (e.g., MoodTracker, ParentView)                               |
| `usf`   | useState + useEffect scaffold            | Modules with timers, async fetches (e.g., hydration timer, calendar sync) |
| `imrn`  | import React Native core components      | Fast setup for RN screen layout                                           |
| `rnfs`  | React Native functional screen component | Use as Claude starter template                                            |
| `clg`   | console.log()                            | Debug Supabase fetches, component state                                   |
| `imp`   | import ... from ...                      | Shorten long import blocks                                                |
| `redux` | Generates Redux action/reducer/slice     | If you later shift into Redux for shared logic                            |
| `nfn`   | function name() {}                       | When writing helpers (e.g., formatTime, parseMoodLevel)                   |
| `ptor`  | PropTypes for objects                    | Optional: good for documenting complex props (e.g. supplement object)     |

## 🔁 Example Expansions

### `rafce` - React Arrow Function Component + Export

```javascript
// rafce expands to:
import React from 'react';

const DailyMood = () => {
  return (
    <View>
      <Text>Track Mood</Text>
    </View>
  );
};

export default DailyMood;
```

### `usf` - useState + useEffect Scaffold

```javascript
// usf expands to:
const [state, setState] = useState();
useEffect(() => {
  // Effect logic here
}, []);
```

### `imrn` - Import React Native Core Components

```javascript
// imrn expands to:
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
```

### `rnfs` - React Native Functional Screen Component

```javascript
// rnfs expands to:
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';

const ScreenName = () => {
  return (
    <View style={styles.container}>
      <Text>Screen Content</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
});

export default ScreenName;
```

## 🧠 BONUS SNIPPET SET FOR CLAUDE

### Reusable Claude Macro List for ZenGlow Development

```typescript
// Core React Native Imports
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';

// ZenGlow Specific Imports
import { supabase } from '../database/supabase';
import { ZenSoundProvider } from '../components/ZenSoundProvider';
import { ZenMoonAvatar } from '../components/ZenMoonAvatar';

// Common Hooks Pattern
const [loading, setLoading] = useState(false);
const [data, setData] = useState([]);
const [error, setError] = useState(null);

// Async Data Fetch Pattern
const fetchData = async () => {
  try {
    setLoading(true);
    const { data, error } = await supabase.from('table_name').select('*');

    if (error) throw error;
    setData(data);
  } catch (error) {
    setError(error.message);
    console.log('Fetch error:', error);
  } finally {
    setLoading(false);
  }
};

// useEffect Pattern
useEffect(() => {
  fetchData();
}, []);

// Common JSX Patterns
<View style={styles.container}>
  <Text style={styles.title}>Title</Text>
  <TouchableOpacity style={styles.button} onPress={() => {}}>
    <Text style={styles.buttonText}>Button</Text>
  </TouchableOpacity>
</View>;

// StyleSheet Pattern
const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
```

## 🎯 ZenGlow Specific Patterns

### Mood Tracking Component Pattern

```javascript
const MoodTracker = () => {
  const [mood, setMood] = useState(5);
  const [notes, setNotes] = useState('');

  const saveMood = async () => {
    const { error } = await supabase.from('mood_entries').insert([
      {
        mood_level: mood,
        notes,
        created_at: new Date().toISOString(),
      },
    ]);

    if (error) console.log('Error saving mood:', error);
  };

  return <View style={styles.container}>{/* Mood tracking UI */}</View>;
};
```

### Exercise Player Pattern

```javascript
const ExercisePlayer = ({ exercise }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (isPlaying) {
      // Start exercise timer
    }
  }, [isPlaying]);

  return (
    <View style={styles.playerContainer}>
      <ZenMoonAvatar mood={exercise.mood} />
      {/* Player controls */}
    </View>
  );
};
```

### Supabase Real-time Pattern

```javascript
useEffect(() => {
  const subscription = supabase
    .channel('table_changes')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'table_name' }, (payload) => {
      console.log('Change received!', payload);
      // Handle real-time updates
    })
    .subscribe();

  return () => {
    subscription.unsubscribe();
  };
}, []);
```

## 🚀 Quick Start Commands for Claude

When working on ZenGlow components, use these as starting points:

1. **New Screen**: Start with `rafce` or `rnfs`
2. **Data Fetching**: Add `usf` pattern with Supabase
3. **Real-time Updates**: Use Supabase subscription pattern
4. **Sound Integration**: Import `ZenSoundProvider`
5. **Avatar Integration**: Import `ZenMoonAvatar`
6. **Debugging**: Use `clg` for console logging

## 📱 ZenGlow Component Hierarchy

```
App.js
├── ZenSoundProvider (Context)
├── Navigation
│   ├── HomeScreen
│   ├── MoodTracker
│   ├── ExerciseLibrary
│   ├── ParentView
│   └── Settings
└── Components
    ├── ZenMoonAvatar
    ├── ExercisePlayer
    └── SharedComponents
```

This snippet library enables rapid ZenGlow development with consistent patterns and best practices.
