import { MotiImage, MotiView } from 'moti';
import React from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { PanGestureHandler } from 'react-native-gesture-handler';
import { useZenMoon } from '../../hooks/useZenMoon';
import { Cheek, Eye, Mouth } from './FaceComponents';

export type CompanionMood = 'calm' | 'curious' | 'playful' | 'joyful' | 'focused';

// Enhanced Zen color palette from the showcase
const zenColors = {
  calm: {
    primary: '#4A90E2',
    secondary: '#7BB3F0',
    accent: '#A8D0F7',
    glow: '#2E86DE',
    particle: '#6FAADB',
    texture: '#3498DB',
    shadow: '#2980B9',
  },
  curious: {
    primary: '#E67E22',
    secondary: '#F39C12',
    accent: '#F7DC6F',
    glow: '#D35400',
    particle: '#F39C12',
    texture: '#FF8C42',
    shadow: '#C0392B',
  },
  joyful: {
    primary: '#27AE60',
    secondary: '#58D68D',
    accent: '#85E085',
    glow: '#229954',
    particle: '#48C9B0',
    texture: '#2ECC71',
    shadow: '#1E8449',
  },
  focused: {
    primary: '#8E44AD',
    secondary: '#BB8FCE',
    accent: '#D7BDE2',
    glow: '#7D3C98',
    particle: '#A569BD',
    texture: '#9B59B6',
    shadow: '#6C3483',
  },
  playful: {
    primary: '#E91E63',
    secondary: '#F06292',
    accent: '#F8BBD9',
    glow: '#C2185B',
    particle: '#EC407A',
    texture: '#FF6B9D',
    shadow: '#AD1457',
  },
  sleepy: {
    primary: '#5D4E75',
    secondary: '#8E7CC3',
    accent: '#B39DDB',
    glow: '#512DA8',
    particle: '#7E57C2',
    texture: '#673AB7',
    shadow: '#4A148C',
  },
};

// Dramatic expressions with exaggerated features from the showcase
const expressions = {
  calm: {
    eyeScale: 0.9,
    eyeAngle: 0,
    mouthScale: 1.1,
    mouthCurve: 15,
    cheekSize: 1.2,
    eyebrowAngle: -5,
    specialEffect: 'gentle-glow',
  },
  curious: {
    eyeScale: 1.4,
    eyeAngle: 3,
    mouthScale: 0.8,
    mouthCurve: 8,
    cheekSize: 1.0,
    eyebrowAngle: 15,
    specialEffect: 'sparkle-eyes',
  },
  joyful: {
    eyeScale: 1.2,
    eyeAngle: -8,
    mouthScale: 1.8,
    mouthCurve: 25,
    cheekSize: 1.6,
    eyebrowAngle: -10,
    specialEffect: 'joy-burst',
  },
  focused: {
    eyeScale: 0.7,
    eyeAngle: 0,
    mouthScale: 0.6,
    mouthCurve: 2,
    cheekSize: 0.8,
    eyebrowAngle: 25,
    specialEffect: 'laser-focus',
  },
  playful: {
    eyeScale: 1.3,
    eyeAngle: 5,
    mouthScale: 1.4,
    mouthCurve: 20,
    cheekSize: 1.4,
    eyebrowAngle: -15,
    specialEffect: 'mischief-sparkle',
  },
  sleepy: {
    eyeScale: 0.4,
    eyeAngle: 0,
    mouthScale: 1.2,
    mouthCurve: -5,
    cheekSize: 1.1,
    eyebrowAngle: -20,
    specialEffect: 'dream-drift',
  },
};

export interface ZenMoonAvatarProps {
  mood: CompanionMood;
  enableAura?: boolean;
  enableInteraction?: boolean;
  meditationProgress?: number;
}

export const ZenMoonAvatar: React.FC<ZenMoonAvatarProps> = (props) => {
  const { pan, panResponder, source, animConfig, contextualColors } = useZenMoon(props);

  const currentExpression = expressions[props.mood] || expressions.calm;
  const currentColors = zenColors[props.mood] || zenColors.calm;

  // TODO: The FaceComponents (Cheek, Eye, Mouth) need to be updated to use these new expression values.
  // This is a placeholder to show how the data is now available.

  return (
    <PanGestureHandler onGestureEvent={panResponder as any}>
      <Animated.View
        style={[styles.draggableContainer, { transform: pan.getTranslateTransform() }]}
      >
        <View style={styles.container}>
          {props.enableAura && (
            <MotiView style={[styles.aura, { shadowColor: currentColors.glow }]} />
          )}
          <MotiView style={styles.moonContainer}>
            <MotiImage
              source={source}
              style={styles.image}
              animate={{ opacity: animConfig.opacity, scale: animConfig.scale }}
              transition={{
                type: 'timing',
                duration: animConfig.duration,
                loop: true,
                easing: animConfig.easing,
              }}
            />
            <View style={styles.faceContainer} pointerEvents="none">
              <View style={styles.cheeksContainer}>
                <Cheek
                  expressionStyle={{
                    backgroundColor: currentColors.particle,
                    transform: [{ scale: currentExpression.cheekSize }],
                  }}
                />
                <Cheek
                  expressionStyle={{
                    backgroundColor: currentColors.particle,
                    transform: [{ scale: currentExpression.cheekSize }],
                  }}
                />
              </View>
              <View style={styles.eyesContainer}>
                <Eye expressionStyle={{ transform: [{ scale: currentExpression.eyeScale }] }} />
                <Eye expressionStyle={{ transform: [{ scale: currentExpression.eyeScale }] }} />
              </View>
              <Mouth expressionStyle={{ transform: [{ scale: currentExpression.mouthScale }] }} />
            </View>
          </MotiView>
          {props.enableInteraction && <MotiView style={styles.ripple} />}
        </View>
      </Animated.View>
    </PanGestureHandler>
  );
};

const styles = StyleSheet.create({
  draggableContainer: { alignItems: 'center', justifyContent: 'center' },
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    width: 160,
    height: 160,
  },
  moonContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    width: 120,
    height: 120,
  },
  image: { width: 120, height: 120, borderRadius: 60 },
  faceContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 120,
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  eyesContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: 60,
    position: 'absolute',
    top: 35,
    left: 30,
  },
  mouthBase: {
    width: 36,
    height: 18,
    borderBottomWidth: 2,
    borderBottomColor: '#333',
    borderRadius: 18,
    position: 'absolute',
    bottom: 18,
    left: 42,
  },
  cheeksContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: 80,
    position: 'absolute',
    bottom: 30,
    left: 20,
  },
  ripple: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    zIndex: 1,
    opacity: 0.3,
    backgroundColor: '#FFD700',
  },
  aura: {
    position: 'absolute',
    width: 180,
    height: 180,
    borderRadius: 90,
    shadowOpacity: 0.5,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 0 },
    elevation: 10,
    zIndex: 0,
  },
});
