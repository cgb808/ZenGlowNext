import { 
  CompanionPersonality, 
  CompanionAction, 
  UserContext, 
  CompanionState, 
  AIDecisionContext, 
  MoodType, 
  ActionType,
  TargetElement 
} from '../types/companion';

// Default personality settings
export const DEFAULT_PERSONALITY: CompanionPersonality = {
  responsiveness: 0.7,
  playfulness: 0.6,
  helpfulness: 0.8,
  expressiveness: 0.7,
  chattiness: 0.5,
};

// Context-based messages for different scenarios
export const COMPANION_MESSAGES = {
  welcome: [
    "Hi there! I'm here to help you on your zen journey! 🌙",
    "Welcome! Let's explore some calming activities together! ✨",
    "Hello! I'm your zen companion, ready to guide you! 🧘‍♀️",
  ],
  encouragement: [
    "You're doing great! Keep going! 💪",
    "I believe in you! Take it one breath at a time! 🌸",
    "Amazing progress! You've got this! ⭐",
    "Small steps lead to big changes! 🌱",
  ],
  celebration: [
    "Fantastic work! You completed your session! 🎉",
    "Way to go! You're building great habits! 🌟",
    "Wonderful! I'm so proud of your dedication! 🏆",
    "Outstanding! You're on fire today! 🔥",
  ],
  concern: [
    "I notice you seem a bit stressed. Would you like to try a breathing exercise? 💙",
    "Take a moment to breathe. I'm here if you need help! 🤗",
    "How about we take a short break together? 🌺",
    "Remember, it's okay to pause and reset. You're not alone! 💝",
  ],
  guidance: [
    "Try tapping here to get started! 👆",
    "This section might help you feel better! ✨",
    "I think you'll enjoy this activity! 🌈",
    "Let me show you something calming! 🕊️",
  ],
  idle: [
    "I'm here when you're ready! 😊",
    "Take your time, no rush! 🍃",
    "Enjoying the peaceful moment! 🌙",
    "Ready for the next adventure! ⭐",
  ],
};

// Action rules based on context
export class CompanionBehaviorEngine {
  private personality: CompanionPersonality;
  private lastActions: CompanionAction[] = [];
  private userPreferences: any = {};

  constructor(personality: CompanionPersonality = DEFAULT_PERSONALITY) {
    this.personality = personality;
  }

  /**
   * Main decision-making function for the companion
   */
  decideNextAction(context: AIDecisionContext): CompanionAction {
    const { trigger, userContext, companionState, targetElement } = context;
    
    // Handle different triggers
    switch (trigger) {
      case 'user_tap':
        return this.handleUserTap(userContext, targetElement);
      case 'idle':
        return this.handleIdleState(userContext, companionState);
      case 'screen_change':
        return this.handleScreenChange(userContext);
      case 'mood_change':
        return this.handleMoodChange(userContext);
      case 'timer':
        return this.handleTimerEvent(userContext, companionState);
      case 'element_appeared':
        return this.handleNewElement(targetElement, userContext);
      default:
        return { type: 'idle' };
    }
  }

  private handleUserTap(userContext: UserContext, targetElement?: TargetElement): CompanionAction {
    if (targetElement) {
      // Look at the tapped element with some personality-based variation
      const intensity = this.personality.expressiveness;
      return {
        type: 'lookAt',
        payload: {
          x: targetElement.x + targetElement.width / 2,
          y: targetElement.y + targetElement.height / 2,
          intensity,
          duration: 1000 + (intensity * 1000), // 1-2 seconds based on expressiveness
        },
      };
    }

    // If no specific element, show curiosity
    return {
      type: 'nod',
      payload: {
        message: this.getRandomMessage('idle'),
        duration: 800,
      },
    };
  }

  private handleIdleState(userContext: UserContext, companionState: CompanionState): CompanionAction {
    const { timeIdle, lastUserAction, currentScreen } = userContext;

    // User has been idle for a while - maybe offer help
    if (timeIdle > 30000 && this.personality.helpfulness > 0.6) {
      return {
        type: 'wave',
        payload: {
          message: this.getRandomMessage('guidance'),
          duration: 2000,
        },
      };
    }

    // User is scrolling or typing - hide to avoid distraction
    if (lastUserAction === 'scroll' || lastUserAction === 'typing') {
      return {
        type: 'hide',
        payload: {
          duration: 5000, // Hide for 5 seconds
        },
      };
    }

    // Just be idle with subtle floating animation
    return { type: 'idle' };
  }

  private handleScreenChange(userContext: UserContext): CompanionAction {
    const { currentScreen, isFirstTime } = userContext;

    // Welcome message for first-time users
    if (isFirstTime && this.personality.chattiness > 0.5) {
      return {
        type: 'wave',
        payload: {
          message: this.getRandomMessage('welcome'),
          duration: 3000,
        },
      };
    }

    // Screen-specific behaviors
    switch (currentScreen) {
      case 'meditation':
        return {
          type: 'awaken',
          payload: {
            message: "Let's find some peace together! 🧘‍♀️",
            intensity: 0.3, // Gentle awakening for meditation
          },
        };
      
      case 'parent-dashboard':
        return {
          type: 'point',
          payload: {
            message: "Great to see you checking in! 📊",
            intensity: 0.6,
          },
        };

      case 'routine':
        return {
          type: 'celebrate',
          payload: {
            message: "Time to build healthy habits! 🌱",
            intensity: 0.7,
          },
        };

      default:
        return { type: 'awaken' };
    }
  }

  private handleMoodChange(userContext: UserContext): CompanionAction {
    const { userMood } = userContext;

    switch (userMood) {
      case 'excited':
        return {
          type: 'celebrate',
          payload: {
            message: this.getRandomMessage('celebration'),
            intensity: this.personality.playfulness,
            duration: 2000,
          },
        };

      case 'concerned':
        return {
          type: 'nod',
          payload: {
            message: this.getRandomMessage('concern'),
            intensity: 0.5, // Gentle, supportive
            duration: 3000,
          },
        };

      case 'calm':
        return {
          type: 'idle',
          payload: {
            message: this.getRandomMessage('idle'),
            intensity: 0.3,
          },
        };

      default:
        return { type: 'idle' };
    }
  }

  private handleTimerEvent(userContext: UserContext, companionState: CompanionState): CompanionAction {
    const { sessionDuration } = userContext;
    
    // Celebrate milestones
    if (sessionDuration > 0 && sessionDuration % 300000 === 0) { // Every 5 minutes
      return {
        type: 'celebrate',
        payload: {
          message: this.getRandomMessage('encouragement'),
          duration: 2000,
        },
      };
    }

    // Check if companion should re-appear after being hidden
    if (companionState.isHidden) {
      return { type: 'awaken' };
    }

    return { type: 'idle' };
  }

  private handleNewElement(targetElement?: TargetElement, userContext?: UserContext): CompanionAction {
    if (!targetElement || this.personality.responsiveness < 0.5) {
      return { type: 'idle' };
    }

    // Point to important new elements
    if (targetElement.type === 'notification' || targetElement.type === 'alert') {
      return {
        type: 'point',
        payload: {
          x: targetElement.x + targetElement.width / 2,
          y: targetElement.y + targetElement.height / 2,
          message: "Something new appeared! 👀",
          duration: 2500,
        },
      };
    }

    // Just look at regular new elements
    return {
      type: 'lookAt',
      payload: {
        x: targetElement.x + targetElement.width / 2,
        y: targetElement.y + targetElement.height / 2,
        duration: 1500,
      },
    };
  }

  /**
   * Determine if companion should intervene based on user context
   */
  shouldIntervene(userContext: UserContext): boolean {
    const { timeIdle, lastUserAction, sessionDuration } = userContext;
    
    // Intervention thresholds based on personality
    const helpfulnessThreshold = this.personality.helpfulness * 45000; // Up to 45 seconds
    const responsivenessThreshold = this.personality.responsiveness * 30000; // Up to 30 seconds

    // User seems stuck or confused (long idle time)
    if (timeIdle > helpfulnessThreshold && lastUserAction !== 'typing') {
      return true;
    }

    // Very long session - suggest a break
    if (sessionDuration > 1800000 && this.personality.helpfulness > 0.7) { // 30 minutes
      return true;
    }

    return false;
  }

  /**
   * Generate contextual mood based on user behavior
   */
  suggestMood(userContext: UserContext): MoodType {
    const { lastUserAction, timeIdle, currentScreen } = userContext;

    if (lastUserAction === 'tap' && timeIdle < 5000) {
      return 'curious';
    }

    if (currentScreen === 'meditation') {
      return 'calm';
    }

    if (timeIdle > 20000) {
      return 'supportive';
    }

    return 'calm';
  }

  /**
   * Get random message from category
   */
  private getRandomMessage(category: keyof typeof COMPANION_MESSAGES): string {
    const messages = COMPANION_MESSAGES[category];
    return messages[Math.floor(Math.random() * messages.length)];
  }

  /**
   * Update personality settings
   */
  updatePersonality(newPersonality: Partial<CompanionPersonality>): void {
    this.personality = { ...this.personality, ...newPersonality };
  }

  /**
   * Record action for learning purposes
   */
  recordAction(action: CompanionAction): void {
    this.lastActions.push(action);
    // Keep only last 10 actions for memory efficiency
    if (this.lastActions.length > 10) {
      this.lastActions.shift();
    }
  }
}

// Export singleton instance for use across the app
export const companionBehaviorEngine = new CompanionBehaviorEngine();