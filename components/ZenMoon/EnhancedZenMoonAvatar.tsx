import React, { useState, useEffect, useMemo, useRef, useCallback, forwardRef, useImperativeHandle, RefObject } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withTiming, Easing, withSequence, withRepeat, withDelay, runOnJS } from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path } from 'react-native-svg';
import { useZenSound } from '../Audio/ZenSoundProvider';
import { Sparkle } from './Sparkle';

// NOTE: This is a React Native translation of the web-based showcase.
// Some features like the particle system and advanced CSS animations are not yet included.

export type MoodType = 'calm' | 'joyful' | 'curious' | 'focused' | 'playful' | 'sleepy';

interface SparkleConfig {
  /** Number of sparkles to show */
  count?: number;
  /** Color of sparkles */
  color?: string;
  /** Duration of sparkle animation */
  duration?: number;
  /** Whether sparkles should repeat */
  repeat?: boolean;
}

interface InactivityConfig {
  /** Timeout in milliseconds before showing suggestion (default: 7000) */
  timeout?: number;
  /** Whether inactivity detection is enabled */
  enabled?: boolean;
}

interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  glow: string;
  shadow: string;
}

interface Expression {
  eyeScale: number;
  mouthCurve: number;
  mouthScale: number;
}

interface EnhancedZenMoonAvatarProps {
  mood?: MoodType;
  size?: number;
  /** Refs to buttons that the moon can suggest when inactive */
  suggestedButtonRefs?: RefObject<View>[];
  /** Configuration for sparkle effects */
  sparkleConfig?: SparkleConfig;
  /** Configuration for inactivity detection */
  inactivityConfig?: InactivityConfig;
  /** Callback when user interaction is detected */
  onUserInteraction?: () => void;
}

export interface EnhancedZenMoonAvatarRef {
  handleUserInteraction: () => void;
}

interface DramaticMouthProps {
  mood: MoodType;
  expression: Expression;
}

const zenColors: Record<MoodType, ColorPalette> = {
    calm: { primary: '#4A90E2', secondary: '#7BB3F0', accent: '#A8D0F7', glow: '#2E86DE', shadow: '#2980B9' },
    joyful: { primary: '#27AE60', secondary: '#58D68D', accent: '#85E085', glow: '#229954', shadow: '#1E8449' },
    curious: { primary: '#E67E22', secondary: '#F39C12', accent: '#F7DC6F', glow: '#D35400', shadow: '#C0392B' },
    focused: { primary: '#8E44AD', secondary: '#BB8FCE', accent: '#D7BDE2', glow: '#7D3C98', shadow: '#6C3483' },
    playful: { primary: '#E91E63', secondary: '#F06292', accent: '#F8BBD9', glow: '#C2185B', shadow: '#AD1457' },
    sleepy: { primary: '#5D4E75', secondary: '#8E7CC3', accent: '#B39DDB', glow: '#512DA8', shadow: '#4A148C' },
};

const expressions: Record<MoodType, Expression> = {
    calm: { eyeScale: 0.9, mouthCurve: 15, mouthScale: 1.1 },
    joyful: { eyeScale: 1.2, mouthCurve: 25, mouthScale: 1.8 },
    curious: { eyeScale: 1.4, mouthCurve: 8, mouthScale: 0.8 },
    focused: { eyeScale: 0.7, mouthCurve: 2, mouthScale: 0.6 },
    playful: { eyeScale: 1.3, mouthCurve: 20, mouthScale: 1.4 },
    sleepy: { eyeScale: 0.4, mouthCurve: -5, mouthScale: 1.2 },
};

const AnimatedPath = Animated.createAnimatedComponent(Path);

const DramaticMouth: React.FC<DramaticMouthProps> = ({ mood, expression }) => {
    const colors = zenColors[mood];
    const mouthPath = `M ${24 - expression.mouthCurve} ${16 - expression.mouthCurve/2} Q 24 ${16 + expression.mouthCurve} ${24 + expression.mouthCurve} ${16 - expression.mouthCurve/2}`;
    
    const animatedStyle = useAnimatedStyle(() => {
        return {
            transform: [{ scale: withSpring(expression.mouthScale) }]
        };
    });

    return (
        <Animated.View style={animatedStyle}>
            <Svg width="48" height="32">
                <Path
                    d={mouthPath}
                    stroke={colors.primary}
                    strokeWidth={3}
                    strokeLinecap="round"
                    fill="none"
                />
            </Svg>
        </Animated.View>
    );
};

interface DramaticEyeProps {
  mood: MoodType;
  expression: Expression;
  isBlinking: boolean;
  rotation?: Animated.SharedValue<number>;
}

const DramaticEye: React.FC<DramaticEyeProps> = ({ mood, expression, isBlinking, rotation }) => {
    const colors = zenColors[mood];
    
    const eyeStyle = useAnimatedStyle(() => {
        return {
            transform: [
                { scale: withSpring(expression.eyeScale) },
                { scaleY: withTiming(isBlinking ? 0.1 : 1, { duration: 100 }) },
                { rotate: `${rotation?.value || 0}deg` }
            ],
        };
    });

    return (
        <Animated.View style={[styles.eyeBase, { backgroundColor: colors.primary }, eyeStyle]}>
            <View style={[styles.pupil, { backgroundColor: colors.shadow }]} />
            <View style={[styles.highlight, { backgroundColor: colors.accent }]} />
        </Animated.View>
    );
};

export const EnhancedZenMoonAvatar = forwardRef<EnhancedZenMoonAvatarRef, EnhancedZenMoonAvatarProps>(({
    mood = 'calm',
    size = 120,
    suggestedButtonRefs = [],
    sparkleConfig = {},
    inactivityConfig = {},
    onUserInteraction,
}, ref) => {
    const [isBlinking, setIsBlinking] = useState(false);
    const [isShowingSuggestion, setIsShowingSuggestion] = useState(false);
    const [currentSuggestedButtonIndex, setCurrentSuggestedButtonIndex] = useState(0);
    
    const colors = zenColors[mood] || zenColors.calm;
    const expression = expressions[mood] || expressions.calm;
    
    // Sound system
    const { playCharacterSound } = useZenSound();
    
    // Configuration with defaults
    const sparkleConf: Required<SparkleConfig> = {
        count: 4,
        color: colors.accent,
        duration: 1500,
        repeat: true,
        ...sparkleConfig,
    };
    
    const inactivityConf: Required<InactivityConfig> = {
        timeout: 7000, // 7 seconds
        enabled: true,
        ...inactivityConfig,
    };
    
    // Refs and timers
    const inactivityTimerRef = useRef<NodeJS.Timeout>();
    const lastInteractionTimeRef = useRef<number>(Date.now());
    
    // Animation values
    const moonTranslateX = useSharedValue(0);
    const moonTranslateY = useSharedValue(0);
    const eyeRotationLeft = useSharedValue(0);
    const eyeRotationRight = useSharedValue(0);
    const showSparkles = useSharedValue(0);
    
    // Reset inactivity timer
    const resetInactivityTimer = useCallback(() => {
        if (inactivityTimerRef.current) {
            clearTimeout(inactivityTimerRef.current);
        }
        
        lastInteractionTimeRef.current = Date.now();
        
        if (inactivityConf.enabled && suggestedButtonRefs.length > 0) {
            inactivityTimerRef.current = setTimeout(() => {
                setIsShowingSuggestion(true);
                showSuggestion();
            }, inactivityConf.timeout);
        }
    }, [inactivityConf.enabled, inactivityConf.timeout, suggestedButtonRefs.length]);
    
    // Show suggestion animation sequence
    const showSuggestion = useCallback(async () => {
        if (suggestedButtonRefs.length === 0) return;
        
        // Select a random button to suggest
        const buttonIndex = Math.floor(Math.random() * suggestedButtonRefs.length);
        setCurrentSuggestedButtonIndex(buttonIndex);
        
        // Play sound effect
        try {
            await playCharacterSound('maybe'); // "hmmm" sound
        } catch (error) {
            console.warn('Failed to play suggestion sound:', error);
        }
        
        // Animation sequence: fly to button, look around, show sparkles
        const targetRef = suggestedButtonRefs[buttonIndex];
        if (targetRef.current) {
            // Calculate position (simplified - in real implementation would measure actual positions)
            const targetX = (buttonIndex - suggestedButtonRefs.length / 2) * 100;
            const targetY = -60;
            
            // Animate moon flying to button
            moonTranslateX.value = withTiming(targetX, { duration: 800, easing: Easing.out(Easing.ease) });
            moonTranslateY.value = withTiming(targetY, { duration: 800, easing: Easing.out(Easing.ease) });
            
            // Animate eyes looking at button, then around
            setTimeout(() => {
                eyeRotationLeft.value = withSequence(
                    withTiming(10, { duration: 300 }),
                    withTiming(-10, { duration: 600 }),
                    withTiming(10, { duration: 600 }),
                    withTiming(0, { duration: 300 })
                );
                eyeRotationRight.value = withSequence(
                    withTiming(10, { duration: 300 }),
                    withTiming(-10, { duration: 600 }),
                    withTiming(10, { duration: 600 }),
                    withTiming(0, { duration: 300 })
                );
                
                // Show sparkles around button
                showSparkles.value = withSequence(
                    withDelay(200, withTiming(1, { duration: 300 })),
                    withTiming(1, { duration: 2000 }),
                    withTiming(0, { duration: 500 })
                );
            }, 800);
            
            // Return to original position after a delay
            setTimeout(() => {
                moonTranslateX.value = withTiming(0, { duration: 1000, easing: Easing.inOut(Easing.ease) });
                moonTranslateY.value = withTiming(0, { duration: 1000, easing: Easing.inOut(Easing.ease) });
                setIsShowingSuggestion(false);
            }, 4000);
        }
    }, [suggestedButtonRefs, playCharacterSound]);
    
    // Handle user interaction
    const handleUserInteraction = useCallback(() => {
        if (isShowingSuggestion) {
            // User interacted during suggestion - return moon to center immediately
            moonTranslateX.value = withTiming(0, { duration: 600, easing: Easing.out(Easing.ease) });
            moonTranslateY.value = withTiming(0, { duration: 600, easing: Easing.out(Easing.ease) });
            eyeRotationLeft.value = withTiming(0, { duration: 300 });
            eyeRotationRight.value = withTiming(0, { duration: 300 });
            showSparkles.value = withTiming(0, { duration: 300 });
            setIsShowingSuggestion(false);
        }
        
        resetInactivityTimer();
        onUserInteraction?.();
    }, [isShowingSuggestion, resetInactivityTimer, onUserInteraction]);
    
    // Initialize inactivity timer
    useEffect(() => {
        resetInactivityTimer();
        return () => {
            if (inactivityTimerRef.current) {
                clearTimeout(inactivityTimerRef.current);
            }
        };
    }, [resetInactivityTimer]);

    useEffect(() => {
        const blinkInterval = setInterval(() => {
            setIsBlinking(true);
            setTimeout(() => setIsBlinking(false), 150);
        }, 3000 + Math.random() * 2000);
        return () => clearInterval(blinkInterval);
    }, [mood]);

    const auraScale = useSharedValue(1);
    useEffect(() => {
        auraScale.value = withRepeat(
            withSequence(
                withTiming(1.1, { duration: 1500, easing: Easing.inOut(Easing.ease) }),
                withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.ease) })
            ), -1, true
        );
    }, [mood]);
    
    const auraStyle = useAnimatedStyle(() => ({
        transform: [{ scale: auraScale.value }]
    }));
    
    // Moon movement animation style
    const moonMovementStyle = useAnimatedStyle(() => ({
        transform: [
            { translateX: moonTranslateX.value },
            { translateY: moonTranslateY.value }
        ]
    }));
    
    // Sparkles animation style
    const sparklesStyle = useAnimatedStyle(() => ({
        opacity: showSparkles.value,
    }));

    // Expose interaction handler for parent components
    useImperativeHandle(ref, () => ({
        handleUserInteraction,
    }), [handleUserInteraction]);

    return (
        <Animated.View style={[{ width: size + 80, height: size + 80, alignItems: 'center', justifyContent: 'center' }, moonMovementStyle]}>
            <Animated.View style={[styles.aura, { width: size + 40, height: size + 40, borderRadius: (size + 40) / 2, backgroundColor: colors.glow+'50' }, auraStyle]} />
            <LinearGradient
                colors={[colors.primary, colors.secondary, colors.accent]}
                style={[styles.moonBase, { width: size, height: size, borderRadius: size / 2 }]}
            >
                <View style={styles.faceContainer}>
                    <View style={styles.eyesContainer}>
                        <DramaticEye mood={mood} expression={expression} isBlinking={isBlinking} rotation={eyeRotationLeft} />
                        <DramaticEye mood={mood} expression={expression} isBlinking={isBlinking} rotation={eyeRotationRight} />
                    </View>
                    <DramaticMouth mood={mood} expression={expression} />
                </View>
            </LinearGradient>
            
            {/* Sparkles around suggested button area */}
            {isShowingSuggestion && (
                <Animated.View style={[styles.sparklesContainer, sparklesStyle]}>
                    {Array.from({ length: sparkleConf.count }, (_, index) => (
                        <Sparkle
                            key={index}
                            color={sparkleConf.color}
                            size={8 + Math.random() * 6}
                            duration={sparkleConf.duration}
                            delay={index * 200}
                            repeat={sparkleConf.repeat}
                            offsetX={(Math.random() - 0.5) * 60}
                            offsetY={(Math.random() - 0.5) * 60}
                        />
                    ))}
                </Animated.View>
            )}
        </Animated.View>
    );
});

const styles = StyleSheet.create({
    aura: {
        position: 'absolute',
    },
    moonBase: {
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.5)',
    },
    faceContainer: {
        ...StyleSheet.absoluteFillObject,
        alignItems: 'center',
        justifyContent: 'center',
    },
    eyesContainer: {
        flexDirection: 'row',
        width: '50%',
        justifyContent: 'space-between',
        position: 'absolute',
        top: '30%',
    },
    eyeBase: {
        width: 16,
        height: 16,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    pupil: {
        width: '40%',
        height: '40%',
        borderRadius: 4,
    },
    highlight: {
        width: '25%',
        height: '25%',
        borderRadius: 2,
        position: 'absolute',
        top: '25%',
        left: '30%',
        opacity: 0.9,
    },
    sparklesContainer: {
        position: 'absolute',
        width: 100,
        height: 100,
        justifyContent: 'center',
        alignItems: 'center',
        top: '50%',
        left: '50%',
        marginTop: -50,
        marginLeft: -50,
    },
});