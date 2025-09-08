/**
 * =================================================================================
 * SENSOR BUFFER TYPES - Type definitions for sensor buffering system
 * =================================================================================
 * Purpose: Centralized type definitions for local sensor data buffering
 * Features:
 * - Strong typing for sensor readings
 * - Transport adapter interfaces
 * - Configuration types
 * =================================================================================
 */

export interface SensorReading {
  id?: number;
  sensor_type: string;
  value: number;
  quality: number;
  ts: number;
  flushed: number;
}

export interface SensorReadingInput {
  sensor_type: string;
  value: number;
  quality: number;
  ts?: number; // Optional, defaults to current timestamp
}

export interface FlushConfig {
  /** Interval in milliseconds for periodic flushing */
  flushInterval: number;
  /** Maximum batch size before forcing a flush */
  batchSize: number;
  /** Maximum age of readings before forcing a flush (milliseconds) */
  maxAge: number;
  /** Enable app state monitoring for flushing */
  enableAppStateFlush: boolean;
}

export interface TransportResult {
  success: boolean;
  error?: string;
  flushedCount?: number;
}

export interface TransportAdapter {
  /**
   * Send a batch of sensor readings to remote service
   * @param readings Array of sensor readings to send
   * @returns Promise resolving to transport result
   */
  sendBatch(readings: SensorReading[]): Promise<TransportResult>;
}

export interface SensorBufferConfig {
  /** Database name */
  databaseName: string;
  /** Flush configuration */
  flush: FlushConfig;
  /** Transport adapter for sending data */
  transport?: TransportAdapter;
  /** Enable debug logging */
  debug?: boolean;
}

export interface BufferStats {
  totalReadings: number;
  pendingReadings: number;
  flushedReadings: number;
  oldestReading?: number;
  newestReading?: number;
}

/**
 * Default configuration for sensor buffer
 */
export const DEFAULT_SENSOR_BUFFER_CONFIG: SensorBufferConfig = {
  databaseName: 'sensor_buffer.db',
  flush: {
    flushInterval: 30000, // 30 seconds
    batchSize: 100,
    maxAge: 300000, // 5 minutes
    enableAppStateFlush: true,
  },
  debug: false,
};