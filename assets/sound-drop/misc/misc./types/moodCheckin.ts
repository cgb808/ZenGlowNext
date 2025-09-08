// Types for manual mood check-ins

export interface MoodCheckin {
  id: string;
  userId: string;
  timestamp: Date;
  mood: 'happy' | 'sad' | 'angry' | 'calm' | 'excited' | 'tired' | 'other';
  notes?: string;
  source: 'child' | 'parent';
}
