// Enhanced ZenGlow Companion Type Definitions

export type MoodType = 'calm' | 'curious' | 'excited' | 'concerned' | 'supportive' | 'focused' | 'playful' | 'sleepy';

export type ActionType = 
  | 'lookAt' 
  | 'nudge' 
  | 'celebrate' 
  | 'hide' 
  | 'awaken' 
  | 'idle'
  | 'point'
  | 'wave'
  | 'nod'
  | 'speak';

export interface TargetElement {
  x: number;
  y: number;
  width: number;
  height: number;
  id?: string;
  type?: string;
}

export interface CompanionAction {
  type: ActionType;
  payload?: {
    x?: number;
    y?: number;
    elementId?: string;
    message?: string;
    duration?: number;
    intensity?: number;
  };
}

export interface UserContext {
  currentScreen: string;
  lastUserAction: 'tap' | 'scroll' | 'typing' | 'idle' | 'navigation';
  timeIdle: number;
  activeElement?: TargetElement;
  userMood?: MoodType;
  timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
  sessionDuration: number;
  isFirstTime?: boolean;
}

export interface CompanionState {
  mood: MoodType;
  isVisible: boolean;
  isHidden: boolean;
  currentAction: CompanionAction;
  position: { x: number; y: number };
  energy: number; // 0-100, affects animation intensity
  attention: number; // 0-100, how focused on user
}

export interface AIDecisionContext {
  trigger: 'user_tap' | 'idle' | 'screen_change' | 'mood_change' | 'timer' | 'element_appeared';
  userContext: UserContext;
  companionState: CompanionState;
  targetElement?: TargetElement;
  previousActions?: CompanionAction[];
}

export interface CompanionPersonality {
  responsiveness: number; // 0-1, how quickly to react
  playfulness: number; // 0-1, tendency for fun interactions
  helpfulness: number; // 0-1, tendency to guide/assist
  expressiveness: number; // 0-1, animation intensity
  chattiness: number; // 0-1, frequency of speaking
}

export interface VoiceSettings {
  enabled: boolean;
  rate: number; // 0.1-1.0
  pitch: number; // 0.5-2.0
  language: string;
  voice?: string;
}

export interface CompanionPreferences {
  personality: CompanionPersonality;
  voice: VoiceSettings;
  animations: {
    enabled: boolean;
    intensity: number; // 0-1
    floatingMotion: boolean;
    expressiveGestures: boolean;
  };
  interactions: {
    autoHide: boolean;
    contextualHints: boolean;
    celebrateAchievements: boolean;
    provideEncouragement: boolean;
  };
}

export interface LearningData {
  userPreferences: {
    preferredInteractionTypes: ActionType[];
    responsiveToMoods: MoodType[];
    commonUsagePatterns: string[];
    ignoredSuggestions: string[];
  };
  sessionHistory: {
    averageSessionLength: number;
    commonScreenTransitions: string[];
    typicalUsageTime: string[];
    frequentActions: string[];
  };
  adaptations: {
    personalityAdjustments: Partial<CompanionPersonality>;
    customMessages: Record<string, string>;
    learnedBehaviors: Record<string, CompanionAction>;
  };
}

export interface CompanionAPI {
  // State management
  getCurrentState: () => CompanionState;
  updateMood: (mood: MoodType) => void;
  updatePosition: (x: number, y: number) => void;
  
  // Actions
  performAction: (action: CompanionAction) => void;
  speak: (message: string, options?: Partial<VoiceSettings>) => Promise<void>;
  hide: (duration?: number) => void;
  show: () => void;
  
  // AI Decision Making
  decideNextAction: (context: AIDecisionContext) => CompanionAction;
  shouldIntervene: (context: UserContext) => boolean;
  generateMessage: (context: UserContext, actionType: ActionType) => string;
  
  // Learning
  recordUserFeedback: (action: CompanionAction, feedback: 'positive' | 'negative' | 'neutral') => void;
  adaptToUser: (learningData: LearningData) => void;
  
  // Accessibility
  announceForScreenReader: (message: string) => void;
  provideTouchGuidance: () => void;
}

// Event types for the companion system
export interface CompanionEvent {
  type: 'action_performed' | 'mood_changed' | 'user_interaction' | 'context_changed';
  timestamp: number;
  data: any;
}

export type CompanionEventListener = (event: CompanionEvent) => void;