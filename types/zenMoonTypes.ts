export interface Position {
  x: number;
  y: number;
}

export interface MovementBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export type MovementType = 'free' | 'constrained' | 'guided';

export interface AnimatedTransform {
  translateX?: number;
  translateY?: number;
  scale?: number;
  rotate?: string;
  opacity?: number;
}

export interface PositionUtils {
  moveToPosition: (position: Position, duration?: number) => void;
  animateToPosition: (position: Position, duration?: number) => Promise<void>;
  constrainPosition: (position: Position, bounds: MovementBounds) => Position;
  snapToGrid: (position: Position, gridSize: number) => Position;
  resetPosition: () => void;
}

export type ExpressionName = 'neutral' | 'happy' | 'joyful' | 'focused' | 'sleepy' | 'excited';

export interface FaceComponentProps {
  expressionStyle?: any;
  isAnimating?: boolean;
  animationDuration?: number;
}

export interface EyeProps extends FaceComponentProps {
  isBlinking?: boolean;
  blinkFrequency?: number;
}

export interface MouthProps extends FaceComponentProps {
  isSpeaking?: boolean;
  emotion?: ExpressionName;
}

export interface CheekProps extends FaceComponentProps {
  glowIntensity?: number; // 0-1
}
