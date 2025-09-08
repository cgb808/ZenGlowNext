// Types for environmental sensors

export interface EnvironmentalSensorData {
  timestamp: Date;
  noiseLevel: number; // dB
  lightLevel: number; // lux
}
