# Focus Exercises Schema and Library

This module defines the structure and content for guided focus/meditation exercises in ZenGlow. It provides TypeScript interfaces, a curated set of exercises, and utility functions for filtering and selection.

## Interfaces

```ts
import { SoundName } from '../hooks/useZenSound';
import { ExpressionName } from '../components/FaceFeatures';

export interface ExerciseStep {
  instruction: string;
  durationSeconds: number;
  moonExpression: ExpressionName;
  cueSound?: SoundName;
}

export interface FocusExercise {
  id: string;
  title: string;
  description: string;
  totalDurationMinutes: number;
  focusSound?: SoundName;
  steps: ExerciseStep[];
}
```

## Example: Focus Exercise Object

```ts
const example: FocusExercise = {
  id: 'gentle-start-1',
  title: 'Gentle Start',
  description: 'A quick, one-minute reset for your mind.',
  totalDurationMinutes: 1,
  steps: [
    {
      instruction: 'Take one deep, slow breath to center yourself.',
      durationSeconds: 15,
      moonExpression: 'neutral',
      cueSound: 'chime',
    },
    // ...more steps...
  ],
};
```

## Library: `guidedExercises`

- Array of curated `FocusExercise` objects for use in the app.
- Each exercise includes a sequence of steps, optional focus sound, and metadata.

## Utility Functions

- `getExercisesByDuration(maxMinutes)` — Filter exercises by total duration.
- `getExercisesByType(type)` — Filter by type/benefit (relaxation, focus, energy, emotional).
- `getRandomExercise()` — Get a random exercise from the library.

## Usage Example

```ts
import { guidedExercises, getExercisesByDuration, getRandomExercise } from './focusExercises';

const quickExercises = getExercisesByDuration(5);
const random = getRandomExercise();
```

## Related

- Depends on: `useZenSound` (for SoundName), `FaceFeatures` (for ExpressionName)
- Used by: Exercise player UI, onboarding, and focus modules
