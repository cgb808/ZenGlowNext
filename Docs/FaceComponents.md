# FaceComponents

Reusable animated facial feature components for ZenGlow avatars.

## Components

- `Eye`: Animated eye, supports scaleY for blinking/expressions
- `Mouth`: Animated mouth, supports style for emotion
- `Cheek`: Animated cheek, supports style for emotion

## Usage

```tsx
import { Eye, Mouth, Cheek } from './FaceComponents';
<Eye expressionStyle={...} />
<Mouth expressionStyle={...} />
<Cheek expressionStyle={...} />
```

## Props

- `expressionStyle`: Style object for emotion/animation
