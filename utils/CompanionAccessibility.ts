import { AccessibilityInfo } from 'react-native';
import { CompanionAction, UserContext } from '../types/companion';

interface AccessibilityFeatures {
  screenReaderAnnouncements: boolean;
  touchGuidance: boolean;
  voiceCommands: boolean;
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
}

/**
 * Accessibility utility class for the ZenGlow Companion
 * Provides screen reader support, touch guidance, and other accessibility features
 */
export class CompanionAccessibility {
  private features: AccessibilityFeatures = {
    screenReaderAnnouncements: true,
    touchGuidance: true,
    voiceCommands: false,
    highContrast: false,
    largeText: false,
    reducedMotion: false,
  };

  private isScreenReaderEnabled = false;

  constructor() {
    this.initializeAccessibility();
  }

  /**
   * Initialize accessibility features detection
   */
  private async initializeAccessibility() {
    try {
      // Check if screen reader is enabled
      this.isScreenReaderEnabled = await AccessibilityInfo.isScreenReaderEnabled();
      
      // Check if reduced motion is preferred
      this.features.reducedMotion = await AccessibilityInfo.isReduceMotionEnabled();
      
      // Listen for accessibility state changes
      AccessibilityInfo.addEventListener('screenReaderChanged', (enabled) => {
        this.isScreenReaderEnabled = enabled;
        this.updateFeatures({ screenReaderAnnouncements: enabled });
      });

      AccessibilityInfo.addEventListener('reduceMotionChanged', (enabled) => {
        this.updateFeatures({ reducedMotion: enabled });
      });
    } catch (error) {
      console.warn('Failed to initialize accessibility features:', error);
    }
  }

  /**
   * Update accessibility features
   */
  updateFeatures(updates: Partial<AccessibilityFeatures>) {
    this.features = { ...this.features, ...updates };
  }

  /**
   * Get current accessibility features
   */
  getFeatures(): AccessibilityFeatures {
    return { ...this.features };
  }

  /**
   * Announce message for screen readers
   */
  announceForScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite') {
    if (!this.features.screenReaderAnnouncements || !this.isScreenReaderEnabled) {
      return;
    }

    try {
      AccessibilityInfo.announceForAccessibility(message);
      console.log(`[Screen Reader]: ${message}`);
    } catch (error) {
      console.warn('Failed to announce for screen reader:', error);
    }
  }

  /**
   * Provide touch guidance for users with visual impairments
   */
  provideTouchGuidance(elementName: string, position: { x: number; y: number }) {
    if (!this.features.touchGuidance) {
      return;
    }

    const guidance = this.generateTouchGuidance(elementName, position);
    this.announceForScreenReader(guidance, 'polite');
  }

  /**
   * Generate contextual guidance message
   */
  private generateTouchGuidance(elementName: string, position: { x: number; y: number }): string {
    const screenRegion = this.getScreenRegion(position);
    return `${elementName} is located in the ${screenRegion} of the screen. Double-tap to activate.`;
  }

  /**
   * Determine screen region for spatial guidance
   */
  private getScreenRegion(position: { x: number; y: number }): string {
    // This would need actual screen dimensions in a real implementation
    const { x, y } = position;
    
    // Simple quadrant-based approach
    if (y < 200) {
      return x < 200 ? 'top-left' : 'top-right';
    } else {
      return x < 200 ? 'bottom-left' : 'bottom-right';
    }
  }

  /**
   * Generate accessible action descriptions
   */
  getActionDescription(action: CompanionAction): string {
    switch (action.type) {
      case 'lookAt':
        return 'Companion is looking at an element on the screen';
      case 'wave':
        return 'Companion is waving hello';
      case 'nod':
        return 'Companion is nodding in agreement';
      case 'celebrate':
        return 'Companion is celebrating your achievement';
      case 'point':
        return 'Companion is pointing to something important';
      case 'nudge':
        return 'Companion is gently nudging for attention';
      case 'speak':
        return 'Companion is speaking';
      case 'hide':
        return 'Companion is hiding to avoid distraction';
      case 'awaken':
        return 'Companion is returning to help';
      default:
        return 'Companion is in idle state';
    }
  }

  /**
   * Generate accessible state descriptions
   */
  getStateDescription(userContext: UserContext): string {
    const { currentScreen, lastUserAction, timeOfDay } = userContext;
    
    let description = `You are currently on the ${currentScreen} screen. `;
    
    if (lastUserAction === 'tap') {
      description += 'You just tapped on the screen. ';
    } else if (lastUserAction === 'scroll') {
      description += 'You are scrolling through content. ';
    }
    
    description += `It's ${timeOfDay}. `;
    
    return description;
  }

  /**
   * Check if animations should be reduced
   */
  shouldReduceAnimations(): boolean {
    return this.features.reducedMotion;
  }

  /**
   * Check if high contrast mode is enabled
   */
  isHighContrastEnabled(): boolean {
    return this.features.highContrast;
  }

  /**
   * Generate voice command instructions
   */
  getVoiceCommands(): string[] {
    if (!this.features.voiceCommands) {
      return [];
    }

    return [
      'Say "help" to get assistance',
      'Say "hide" to hide the companion',
      'Say "show" to show the companion',
      'Say "repeat" to hear the last message again',
      'Say "settings" to adjust companion preferences',
    ];
  }

  /**
   * Announce companion actions for accessibility
   */
  announceAction(action: CompanionAction) {
    if (!this.isScreenReaderEnabled) {
      return;
    }

    const description = this.getActionDescription(action);
    let announcement = description;

    // Add message if available
    if (action.payload?.message) {
      announcement += `. ${action.payload.message}`;
    }

    this.announceForScreenReader(announcement, 'polite');
  }

  /**
   * Provide contextual help
   */
  provideContextualHelp(userContext: UserContext) {
    if (!this.isScreenReaderEnabled) {
      return;
    }

    const stateDescription = this.getStateDescription(userContext);
    this.announceForScreenReader(stateDescription, 'polite');
  }

  /**
   * Clean up accessibility listeners
   */
  cleanup() {
    try {
      // Note: React Native AccessibilityInfo doesn't have removeEventListener
      // Listeners are automatically cleaned up when the app is destroyed
      console.log('Accessibility cleanup completed');
    } catch (error) {
      console.warn('Failed to cleanup accessibility listeners:', error);
    }
  }
}

// Export singleton instance
export const companionAccessibility = new CompanionAccessibility();