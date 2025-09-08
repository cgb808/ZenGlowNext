/**
 * =================================================================================
 * SENSOR DATA TYPES - Encrypted Sensor Storage Schema
 * =================================================================================
 * Purpose: Type definitions for sensor data with encryption support
 * Features:
 * - Sensitive field identification for selective encryption
 * - Buffer management for offline sensor data
 * - Quality indicators for sensor readings
 * - Migration support from plaintext storage
 * =================================================================================
 */

/**
 * Raw sensor reading with encryption metadata
 */
export interface SensorReading {
  id: string;
  timestamp: number;
  sensorType: SensorType;
  value: number | string; // SENSITIVE - encrypted in storage
  quality: SensorQuality; // SENSITIVE - encrypted in storage
  metadata?: SensorMetadata;
  encrypted?: boolean; // Migration flag
}

/**
 * Buffered sensor data for offline storage
 */
export interface SensorBuffer {
  childId: string;
  readings: SensorReading[];
  lastSync?: number;
  totalSize: number;
  encrypted: boolean;
}

/**
 * Sensor types supported by the system
 */
export enum SensorType {
  HEART_RATE = 'heart_rate',
  STRESS_LEVEL = 'stress_level',
  BREATHING_RATE = 'breathing_rate',
  ACTIVITY_LEVEL = 'activity_level',
  SLEEP_QUALITY = 'sleep_quality',
  MOOD_INDICATOR = 'mood_indicator',
  ENVIRONMENT_NOISE = 'environment_noise',
  ENVIRONMENT_LIGHT = 'environment_light',
  SCREEN_TIME = 'screen_time',
  ENGAGEMENT_LEVEL = 'engagement_level'
}

/**
 * Quality indicators for sensor readings
 */
export enum SensorQuality {
  EXCELLENT = 'excellent',
  GOOD = 'good',
  FAIR = 'fair',
  POOR = 'poor',
  INVALID = 'invalid'
}

/**
 * Additional sensor metadata
 */
export interface SensorMetadata {
  deviceId?: string;
  batteryLevel?: number;
  signalStrength?: number;
  calibrated?: boolean;
  notes?: string;
}

/**
 * Encryption configuration for sensor data
 */
export interface SensorEncryptionConfig {
  encryptionEnabled: boolean;
  keyRotationInterval: number; // in milliseconds
  encryptedFields: (keyof SensorReading)[];
  algorithm: string;
  keyLength: number;
}

/**
 * Key management for sensor data encryption
 */
export interface SensorEncryptionKey {
  keyId: string;
  key: string;
  createdAt: number;
  expiresAt?: number;
  active: boolean;
  version: number;
}

/**
 * Migration status for plaintext to encrypted data
 */
export interface SensorMigrationStatus {
  inProgress: boolean;
  totalRecords: number;
  migratedRecords: number;
  startedAt?: number;
  completedAt?: number;
  errors: string[];
}

/**
 * Sensor data statistics
 */
export interface SensorDataStats {
  totalReadings: number;
  encryptedReadings: number;
  plaintextReadings: number;
  oldestReading?: number;
  newestReading?: number;
  sensorTypes: Record<SensorType, number>;
  avgQuality: number;
  storageSize: number;
}

/**
 * Default encryption configuration
 */
export const DEFAULT_SENSOR_ENCRYPTION_CONFIG: SensorEncryptionConfig = {
  encryptionEnabled: true,
  keyRotationInterval: 30 * 24 * 60 * 60 * 1000, // 30 days
  encryptedFields: ['value', 'quality'],
  algorithm: 'AES-256-CBC',
  keyLength: 32
};

/**
 * Sensitive sensor types that require extra protection
 */
export const SENSITIVE_SENSOR_TYPES = new Set<SensorType>([
  SensorType.HEART_RATE,
  SensorType.STRESS_LEVEL,
  SensorType.BREATHING_RATE,
  SensorType.SLEEP_QUALITY,
  SensorType.MOOD_INDICATOR
]);

/**
 * Maximum retention periods for different sensor types (in milliseconds)
 */
export const SENSOR_RETENTION_PERIODS: Record<SensorType, number> = {
  [SensorType.HEART_RATE]: 7 * 24 * 60 * 60 * 1000, // 7 days
  [SensorType.STRESS_LEVEL]: 7 * 24 * 60 * 60 * 1000, // 7 days
  [SensorType.BREATHING_RATE]: 3 * 24 * 60 * 60 * 1000, // 3 days
  [SensorType.ACTIVITY_LEVEL]: 14 * 24 * 60 * 60 * 1000, // 14 days
  [SensorType.SLEEP_QUALITY]: 30 * 24 * 60 * 60 * 1000, // 30 days
  [SensorType.MOOD_INDICATOR]: 14 * 24 * 60 * 60 * 1000, // 14 days
  [SensorType.ENVIRONMENT_NOISE]: 1 * 24 * 60 * 60 * 1000, // 1 day
  [SensorType.ENVIRONMENT_LIGHT]: 1 * 24 * 60 * 60 * 1000, // 1 day
  [SensorType.SCREEN_TIME]: 7 * 24 * 60 * 60 * 1000, // 7 days
  [SensorType.ENGAGEMENT_LEVEL]: 7 * 24 * 60 * 60 * 1000, // 7 days
};