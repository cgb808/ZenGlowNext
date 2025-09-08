# ZenGlowCompanion Documentation

This document provides an overview of the `ZenGlowCompanion` component, its architecture, and how to use it.

---

## Overview

The `ZenGlowCompanion` is a floating, interactive UI component that acts as a user's guide and assistant within the ZenGlow app. It is designed to appear context-aware and responsive to user actions, powered by a local AI model.

## Architecture

The system is composed of three main parts:

1.  **`UIElementProvider` (Context)**
    -   **File**: `contexts/UIElementContext.tsx`
    -   **Purpose**: Creates a context that allows any UI component in the app to register its position and dimensions.
    -   **Usage**: Wrap the root of your application with `<UIElementProvider>` to make the context available everywhere.

2.  **`useCompanionAI` (Hook)**
    -   **File**: `hooks/useCompanionAI.ts`
    -   **Purpose**: This hook represents the companion's "brain" (Model 2). It contains the logic for deciding what action the companion should take based on user interaction and UI context. Currently, it contains mock logic, but it is the integration point for a real on-device decision-making model.

3.  **`ZenGlowCompanion` (Component)**
    -   **File**: `components/Companion/ZenGlowCompanion.tsx`
    -   **Purpose**: This is the visual component that the user sees. It is draggable and renders the `ZenMoonAvatar`. It uses the `useCompanionAI` hook to get the current mood and action, and the `useUIElements` context to be aware of other components on the screen.

---

## How to Use

### 1. Make the Companion Aware of a Component

To allow the companion to "see" and interact with a UI element (like a button or card), you need to register that element with the `UIElementProvider`.

In the component you want to be visible to the companion, use the `useUIElements` hook and register the component's layout.

```typescriptreact
import { useUIElements } from '@/contexts/UIElementContext';
import { TouchableOpacity, Text } from 'react-native';

const SomeButton = () => {
    const { registerElement } = useUIElements();
    const elementId = 'my-special-button';

    return (
        <TouchableOpacity
            onLayout={(event) => {
                // Register the component's layout with a unique ID
                registerElement(elementId, event.nativeEvent.layout);
            }}
        >
            <Text>Look At Me!</Text>
        </TouchableOpacity>
    );
}
```

### 2. Root Layout Setup

Your root layout file (`app/_layout.tsx`) must be wrapped with all the necessary providers.

```typescriptreact
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { UIElementProvider, ZenGlowCompanion } from '@/components/Companion/ZenGlowCompanion';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <UIElementProvider>
        {/* ... your other providers and navigation stack ... */}
        <ZenGlowCompanion />
      </UIElementProvider>
    </GestureHandlerRootView>
  );
}
```

This setup ensures the companion can float above all other content and be aware of any UI elements that register themselves.
