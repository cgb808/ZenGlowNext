# ZenGlow App Dependencies

## Core React Native + Navigation

- `react-native`  
- `react`  
- `@react-navigation/native`  
- `@react-navigation/native-stack`  
- `react-native-gesture-handler`  
- `react-native-safe-area-context`  
- `react-native-screens`  
- `react-native-reanimated`  
- `react-native-vector-icons` (if icons needed later)

## State & Storage (Upcoming)

- `@react-native-async-storage/async-storage`  
- `@react-native-community/datetimepicker` *(for calendar input)*

## Audio & Media

- `expo-av` *(for playing sounds, music, and audio feedback)*

## UI (Optional/Future)

- `react-native-paper` or `native-base` *(if you want prebuilt UI components later)*

## Calendar (Planned)

- `react-native-calendars` *(calendar views and mood tracking)*

## Charts (For overview gauges/sliders)

- `react-native-chart-kit`  
- `react-native-svg` *(required peer dep for charts)*

---

## Dev & Metro

- `expo` *(if using Expo setup)*  
- `expo-status-bar` *(Expo status bar component)*
- `react-dom` *(Web support for React Native via Expo/React Native Web)*
- `react-native-web` *(Web support for React Native components)*
- `uuid` *(For generating unique IDs in schemas/data)*
- `expo install` *(to manage native dependencies properly)*  
- `metro-config` *(used in RN v0.73 warning)*

---

Let me know if you're **Expo-managed** or not — so I can tailor this even tighter. Want a script later to check and list missing installs too?

### exerciseSchema.js

Used to validate and load structured exercise/tutorial files. Supports breathing, stretching, and focus activities.
