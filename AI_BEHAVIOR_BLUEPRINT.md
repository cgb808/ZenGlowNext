# AI Behavior Blueprint for ZenGlow Companion

This document outlines a set of behaviors for the AI model controlling the ZenGlow Companion. The model's goal is to take the current UI/user context as input and output a specific action, which then triggers a corresponding mood and animation.

## Core AI Actions & Animations

Here is a distinct set of actions the companion can perform.

### 1. Action: `lookAt(elementId)`

*   **Description**: The companion turns to "gaze" at a specific UI element. This is the primary action for showing contextual awareness.
*   **Trigger**:
    *   User taps the screen.
    *   A new, important UI element appears (e.g., a notification badge).
*   **Mood Change**: `curious`
*   **Animation**: A smooth, spring-based rotation of the avatar to face the target element. The eyes in the ZenMoonAvatar could also animate to look in that direction.

### 2. Action: `nudge(elementId)`

*   **Description**: The companion performs a small, quick "hop" or "nudge" animation towards an interactive element, subtly guiding the user's attention.
*   **Trigger**:
    *   The user has been idle on a screen for a period of time.
    *   The AI identifies a primary action on the screen that the user hasn't taken (e.g., an unclicked "Continue" button).
*   **Mood Change**: `playful`
*   **Animation**: A quick bounce animation where the companion moves slightly towards the target element and then returns to its original position.

### 3. Action: `celebrate()`

*   **Description**: A joyful animation to provide positive reinforcement.
*   **Trigger**:
    *   The user completes a key task (e.g., finishes a meditation session, reaches a goal).
    *   A positive notification or achievement is displayed.
*   **Mood Change**: `joyful`
*   **Animation**: The companion does a happy wiggle, a little spin, or emits a gentle particle effect. The aura could pulse with a warm, bright color.

### 4. Action: `hide()`

*   **Description**: The companion becomes semi-transparent or shrinks to be less obtrusive.
*   **Trigger**:
    *   The user begins typing in a text field.
    *   A video or full-screen content starts playing.
    *   The user is scrolling through a long list of text.
*   **Mood Change**: `focused`
*   **Animation**: A smooth opacity fade to about 20% and a slight scale-down. It should feel like it's politely getting out of the way.

### 5. Action: `awaken()`

*   **Description**: The companion returns to its normal state after being hidden.
*   **Trigger**:
    *   The user stops typing or scrolling.
    *   Full-screen content is dismissed.
*   **Mood Change**: `calm`
*   **Animation**: A smooth fade-in of opacity and scale back to its normal size.

## Training Your Model

To train a small model to control these actions, you would create a dataset that maps a given context to a desired action.

### Example Training Data Point (in JSON format):

```json
{
  "context": {
    "lastUserAction": "scrolling",
    "activeElement": "list_view",
    "timeIdle": 1.2,
    "companionIsHidden": false
  },
  "action": "hide"
}
