import React, { useEffect, useCallback } from 'react';
import { Dimensions, StyleSheet, TouchableOpacity } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { useUIElements } from '../../contexts/UIElementContext';
import { useCompanionAI } from '../../hooks/useCompanionAI';
import { EnhancedZenMoonAvatar, type MoodType } from '../ZenMoon/EnhancedZenMoonAvatar';
import { CompanionAnimations } from './CompanionAnimationsSimple';
import { ActionType } from '../../types/companion';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

export const ZenGlowCompanion: React.FC = () => {
  const { elements } = useUIElements();
  const positionX = useSharedValue(screenWidth - 80);
  const positionY = useSharedValue(screenHeight - 150);
  const rotation = useSharedValue(0);
  const isPressed = useSharedValue(false);
  const pressedScale = useSharedValue(1);

  const { 
    companionState, 
    decideNextAction, 
    updatePosition,
    updateUserContext 
  } = useCompanionAI('default-family', 'default-child');

  // Update position in AI system when companion moves
  const updateAIPosition = useCallback((x: number, y: number) => {
    updatePosition(x, y);
  }, [updatePosition]);

  const lookAt = useCallback((targetX: number, targetY: number) => {
    'worklet';
    const companionCenterX = positionX.value + 40;
    const companionCenterY = positionY.value + 40;
    const angle = Math.atan2(targetY - companionCenterY, targetX - companionCenterX);
    rotation.value = withSpring(angle * (180 / Math.PI) + 90, { damping: 15 });
  }, [positionX, positionY, rotation]);

  const lookIdle = useCallback(() => {
    'worklet';
    rotation.value = withSpring(0, { damping: 15 });
  }, [rotation]);

  // Handle AI actions
  useEffect(() => {
    const action = companionState.currentAction;
    
    if (action.type === 'lookAt' && action.payload?.x && action.payload?.y) {
      lookAt(action.payload.x, action.payload.y);
    } else if (action.type === 'idle') {
      lookIdle();
    }
    
    // Update position in AI system
    updateAIPosition(positionX.value, positionY.value);
  }, [companionState.currentAction, updateAIPosition, positionX.value, positionY.value, lookAt, lookIdle]);

  const panGesture = Gesture.Pan()
    .onBegin(() => {
      isPressed.value = true;
      pressedScale.value = withSpring(1.1);
      // Notify AI about interaction
      runOnJS(updateUserContext)({ lastUserAction: 'tap' });
    })
    .onUpdate((event) => {
      const newX = event.translationX + (screenWidth - 80);
      const newY = event.translationY + (screenHeight - 150);
      positionX.value = newX;
      positionY.value = newY;
      
      // Update AI position tracking
      runOnJS(updateAIPosition)(newX, newY);
    })
    .onEnd(() => {
      const finalX = positionX.value > screenWidth / 2 ? screenWidth - 80 : 10;
      positionX.value = withSpring(finalX);
      
      // Update final position in AI
      runOnJS(updateAIPosition)(finalX, positionY.value);
    })
    .onFinalize(() => {
      isPressed.value = false;
      pressedScale.value = withSpring(1);
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: positionX.value },
      { translateY: positionY.value },
      { scale: pressedScale.value },
    ],
  }));

  const gazeStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  const onScreenTap = () => {
    let closestElement: any = null;
    let minDistance = Infinity;

    Object.values(elements).forEach((layout) => {
      if (!layout) return;
      const elementCenterX = layout.x + layout.width / 2;
      const elementCenterY = layout.y + layout.height / 2;
      const distance = Math.sqrt(
        Math.pow(elementCenterX - (positionX.value + 40), 2) +
          Math.pow(elementCenterY - (positionY.value + 40), 2),
      );
      if (distance < minDistance) {
        minDistance = distance;
        closestElement = layout;
      }
    });

    // Enhanced decision making with full context
    decideNextAction({ 
      trigger: 'user_tap', 
      targetElement: closestElement,
      userContext: {
        currentScreen: 'current', // TODO: Get actual current screen
        lastUserAction: 'tap',
        timeIdle: 0,
        timeOfDay: getCurrentTimeOfDay(),
        sessionDuration: Date.now() - sessionStartTime,
        activeElement: closestElement,
      },
      companionState,
    });
  };

  const sessionStartTime = React.useRef(Date.now()).current;

  const getCurrentTimeOfDay = (): 'morning' | 'afternoon' | 'evening' | 'night' => {
    const hour = new Date().getHours();
    if (hour < 6) return 'night';
    if (hour < 12) return 'morning';
    if (hour < 18) return 'afternoon';
    if (hour < 22) return 'evening';
    return 'night';
  };

  const handleAnimationComplete = useCallback(() => {
    // Reset to idle state after animation completes
    if (companionState.currentAction.type !== 'idle') {
      setTimeout(() => {
        decideNextAction({
          trigger: 'idle',
          userContext: {
            currentScreen: 'current',
            lastUserAction: 'idle',
            timeIdle: 1000,
            timeOfDay: getCurrentTimeOfDay(),
            sessionDuration: Date.now() - sessionStartTime,
          },
          companionState,
        });
      }, 500);
    }
  }, [companionState, decideNextAction, sessionStartTime]);

  return (
    <GestureDetector gesture={panGesture}>
      <Animated.View style={[styles.container, animatedStyle]}>
        <CompanionAnimations
          currentAction={companionState.currentAction.type as ActionType}
          mood={companionState.mood}
          isVisible={companionState.isVisible}
          isHidden={companionState.isHidden}
          energy={companionState.energy}
          intensity={companionState.currentAction.payload?.intensity || 0.7}
          onAnimationComplete={handleAnimationComplete}
        >
          <TouchableOpacity onPress={onScreenTap} activeOpacity={0.8}>
            <Animated.View style={gazeStyle}>
              <EnhancedZenMoonAvatar
                mood={companionState.mood as MoodType}
                size={80}
              />
            </Animated.View>
          </TouchableOpacity>
        </CompanionAnimations>
      </Animated.View>
    </GestureDetector>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    zIndex: 1000,
    width: 160, // Container needs to be larger to hold the aura
    height: 160,
    // Adjust position to account for the larger container size
    bottom: 120,
    right: 0,
  },
});
