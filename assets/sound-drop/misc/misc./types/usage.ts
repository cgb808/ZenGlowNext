// Types for app usage tracking

export interface AppUsageEvent {
  timestamp: Date;
  eventType: 'open' | 'close' | 'feature_use' | 'notification' | 'checkin';
  details?: string;
}

export interface UsageAnalytics {
  dailyActiveUsers: number;
  sessionLengths: number[];
  featureUsage: Record<string, number>;
}
