import { useEffect, useState, useCallback, useRef } from 'react';
import { 
  CompanionAction, 
  CompanionState, 
  UserContext, 
  AIDecisionContext, 
  MoodType,
  TargetElement,
  CompanionPersonality,
  VoiceSettings
} from '../types/companion';
import { companionBehaviorEngine, DEFAULT_PERSONALITY } from '../utils/CompanionPersonality';

// Legacy interface for backward compatibility
interface ActionContext {
  trigger: 'user_tap' | 'idle';
  targetElement?: TargetElement;
}

// Enhanced AI Brain Hook - Now with real intelligence!
export const useCompanionAI = (familyId: string, childId: string) => {
  // Core state
  const [companionState, setCompanionState] = useState<CompanionState>({
    mood: 'calm',
    isVisible: true,
    isHidden: false,
    currentAction: { type: 'idle' },
    position: { x: 0, y: 0 },
    energy: 80,
    attention: 70,
  });

  // User context tracking
  const [userContext, setUserContext] = useState<UserContext>({
    currentScreen: 'unknown',
    lastUserAction: 'idle',
    timeIdle: 0,
    timeOfDay: getCurrentTimeOfDay(),
    sessionDuration: 0,
    isFirstTime: false,
  });

  // Personality and preferences
  const [personality, setPersonality] = useState<CompanionPersonality>(DEFAULT_PERSONALITY);
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({
    enabled: true,
    rate: 0.8,
    pitch: 1.0,
    language: 'en-US',
  });

  // Timers and refs
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const sessionStartRef = useRef<number>(Date.now());
  const lastActionTimeRef = useRef<number>(Date.now());

  // Initialize personality engine
  useEffect(() => {
    companionBehaviorEngine.updatePersonality(personality);
  }, [personality]);

  // Track session duration
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      const sessionDuration = now - sessionStartRef.current;
      const timeSinceLastAction = now - lastActionTimeRef.current;

      setUserContext(prev => ({
        ...prev,
        sessionDuration,
        timeIdle: timeSinceLastAction,
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Monitor for intervention opportunities
  useEffect(() => {
    if (companionBehaviorEngine.shouldIntervene(userContext)) {
      const interventionAction = companionBehaviorEngine.decideNextAction({
        trigger: 'timer',
        userContext,
        companionState,
      });
      
      performAction(interventionAction);
    }
  }, [userContext.timeIdle, userContext.sessionDuration]);

  // Update companion mood based on context
  const updateMoodBasedOnContext = useCallback(() => {
    const suggestedMood = companionBehaviorEngine.suggestMood(userContext);
    if (suggestedMood !== companionState.mood) {
      setCompanionState(prev => ({ ...prev, mood: suggestedMood }));
    }
  }, [userContext, companionState.mood]);

  // Perform a companion action
  const performAction = useCallback((action: CompanionAction) => {
    setCompanionState(prev => ({ ...prev, currentAction: action }));
    companionBehaviorEngine.recordAction(action);

    // Handle action-specific state changes
    switch (action.type) {
      case 'hide':
        setCompanionState(prev => ({ ...prev, isHidden: true, isVisible: false }));
        if (action.payload?.duration) {
          setTimeout(() => {
            setCompanionState(prev => ({ ...prev, isHidden: false, isVisible: true }));
          }, action.payload.duration);
        }
        break;

      case 'awaken':
        setCompanionState(prev => ({ 
          ...prev, 
          isHidden: false, 
          isVisible: true, 
          energy: Math.min(100, prev.energy + 20) 
        }));
        break;

      case 'celebrate':
        setCompanionState(prev => ({ 
          ...prev, 
          mood: 'excited',
          energy: Math.min(100, prev.energy + 30),
          attention: 100
        }));
        break;

      case 'lookAt':
      case 'point':
        setCompanionState(prev => ({ 
          ...prev, 
          mood: 'curious',
          attention: Math.min(100, prev.attention + 20)
        }));
        break;
    }

    // Speak if message is provided and voice is enabled
    if (action.payload?.message && voiceSettings.enabled) {
      speak(action.payload.message);
    }
  }, [voiceSettings.enabled]);

  // Enhanced decision-making function
  const decideNextAction = useCallback((context: ActionContext | AIDecisionContext) => {
    let enhancedContext: AIDecisionContext;

    // Handle legacy ActionContext for backward compatibility
    if ('trigger' in context && Object.keys(context).length <= 2) {
      enhancedContext = {
        trigger: context.trigger,
        userContext,
        companionState,
        targetElement: context.targetElement,
      };
    } else {
      enhancedContext = context as AIDecisionContext;
    }

    // Update user action tracking
    lastActionTimeRef.current = Date.now();
    setUserContext(prev => ({ 
      ...prev, 
      lastUserAction: enhancedContext.trigger === 'user_tap' ? 'tap' : 'idle',
      timeIdle: 0
    }));

    // Get AI decision
    const action = companionBehaviorEngine.decideNextAction(enhancedContext);
    performAction(action);

    return action;
  }, [userContext, companionState, performAction]);

  // Context update functions
  const updateUserContext = useCallback((updates: Partial<UserContext>) => {
    setUserContext(prev => ({ ...prev, ...updates }));
  }, []);

  const updateCurrentScreen = useCallback((screen: string) => {
    setUserContext(prev => ({ ...prev, currentScreen: screen }));
    
    // Trigger screen change action
    const action = companionBehaviorEngine.decideNextAction({
      trigger: 'screen_change',
      userContext: { ...userContext, currentScreen: screen },
      companionState,
    });
    
    performAction(action);
  }, [userContext, companionState, performAction]);

  // Text-to-speech function with real TTS implementation
  const speak = useCallback(async (message: string, options?: Partial<VoiceSettings>) => {
    if (!voiceSettings.enabled) return;

    try {
      // Import TTS dynamically to avoid issues if not available
      const Tts = require('react-native-tts');
      
      // Configure TTS settings
      const ttsOptions = {
        androidParams: {
          KEY_PARAM_PAN: 0,
          KEY_PARAM_VOLUME: 1.0,
        },
        iosVoiceId: voiceSettings.voice || 'com.apple.ttsbundle.Samantha-compact',
        rate: options?.rate || voiceSettings.rate,
        pitch: options?.pitch || voiceSettings.pitch,
        language: options?.language || voiceSettings.language,
      };

      // Set up TTS
      await Tts.setDefaultRate(ttsOptions.rate);
      await Tts.setDefaultPitch(ttsOptions.pitch);
      await Tts.setDefaultLanguage(ttsOptions.language);

      // Speak the message
      await Tts.speak(message, ttsOptions);
      
      console.log(`[Companion Speaking]: ${message}`);
    } catch (error) {
      console.warn('TTS not available, falling back to console log:', error);
      console.log(`[Companion Speaking]: ${message}`);
    }
  }, [voiceSettings]);

  // Utility function to get current time of day
  function getCurrentTimeOfDay(): 'morning' | 'afternoon' | 'evening' | 'night' {
    const hour = new Date().getHours();
    if (hour < 6) return 'night';
    if (hour < 12) return 'morning';
    if (hour < 18) return 'afternoon';
    if (hour < 22) return 'evening';
    return 'night';
  }

  // Update position tracking
  const updatePosition = useCallback((x: number, y: number) => {
    setCompanionState(prev => ({ ...prev, position: { x, y } }));
  }, []);

  // Legacy support - return values expected by existing ZenGlowCompanion
  const nextAction = {
    type: companionState.currentAction.type,
    payload: companionState.currentAction.payload,
  };

  return {
    // Legacy exports for backward compatibility
    mood: companionState.mood,
    nextAction,
    decideNextAction,
    recommendation: null, // Deprecated in favor of action messages

    // Enhanced exports
    companionState,
    userContext,
    personality,
    voiceSettings,
    
    // Action functions
    performAction,
    speak,
    updateUserContext,
    updateCurrentScreen,
    updatePosition,
    
    // State setters for customization
    setPersonality,
    setVoiceSettings,
    
    // Utility functions
    shouldIntervene: () => companionBehaviorEngine.shouldIntervene(userContext),
    getCurrentTimeOfDay,
  };
};
