// Types for wearable device integration

export interface WearableDevice {
  id: string;
  name: string;
  type: 'fitness_tracker' | 'smartwatch' | 'other';
  connected: boolean;
  lastSync: Date | null;
  data: WearableData;
}

export interface WearableData {
  heartRate?: number;
  steps?: number;
  sleep?: {
    duration: number;
    quality: 'good' | 'fair' | 'poor';
  };
  // Add more metrics as needed
}
