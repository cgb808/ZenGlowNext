# UI and Companion AI Interaction

This document explains how the AI system, specifically the Companion Behavior Model, interacts with the ZenGlow user interface.

## The Companion Behavior Model (Model 2)

This is a small, on-device decision-making model that controls the `ZenGlowCompanion` component.

-   **Function**: It controls the UI/UX of the companion, deciding how it should act based on the user's interactions with the app.
-   **Input**: The app's UI context, such as `{"event": "user_scrolling", "active_screen": "dashboard"}`.
-   **Output**: A specific, predefined action for the companion to perform, such as `hide()` or `lookAt('metrics_card')`.

## UI Integration

The integration is handled by the `ZenGlowCompanion.tsx` component, which uses a hook called `useCompanionAI`. This hook is a placeholder for the actual Model 2.

1.  **Context Gathering**: UI elements can register their position on the screen using the `UIElementProvider`. When a user interacts with the app (e.g., tapping the screen), the `ZenGlowCompanion` gathers context about the nearest UI element.
2.  **Decision Making**: This context is passed to the AI model (`decideNextAction` function). The model then returns an action (e.g., `lookAt`, `nudge`).
3.  **Action Execution**: The `ZenGlowCompanion` component receives the action and executes it, for example, by animating the avatar to look towards a specific UI element.

This creates a responsive and intelligent user experience where the companion appears to be aware of and reactive to the user's actions.
