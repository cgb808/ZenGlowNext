# exerciseSchema.js

Defines the structure for exercise tracking data in ZenGlow.

## Fields

- `id` (string): Unique identifier for the exercise entry
- `name` (string): Name of the exercise
- `duration` (number): Duration in minutes
- `type` (string): Type/category of exercise (e.g., focus, movement)
- `timestamp` (string): ISO date/time of the entry
- `notes` (string, optional): Additional notes
- `version` (string): Schema version

## Example

```js
{
  id: "uuid-v4",
  name: "Jumping Jacks",
  duration: 5,
  type: "movement",
  timestamp: "2025-07-12T10:00:00Z",
  notes: "Felt energetic!",
  version: "1.0.0"
}
```

## Usage

Used in: `src/exercises/`, `views/exercises.jsx`, and related logic for tracking and displaying exercise sessions.
