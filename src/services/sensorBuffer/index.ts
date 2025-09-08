/**
 * =================================================================================
 * SENSOR BUFFER MODULE - Export all sensor buffering components
 * =================================================================================
 */

// Main sensor buffer class
export { SensorBuffer } from './SensorBuffer';

// Core components
export { SensorDatabase } from './SensorDatabase';
export { FlushScheduler } from './FlushScheduler';
export type { FlushEvent, FlushTrigger } from './FlushScheduler';

// Transport adapters
export {
  HttpTransportAdapter,
  SupabaseTransportAdapter,
  MockTransportAdapter,
} from './TransportAdapter';

// Types and interfaces
export type {
  SensorReading,
  SensorReadingInput,
  FlushConfig,
  TransportResult,
  TransportAdapter,
  SensorBufferConfig,
  BufferStats,
} from './types';

// Default configuration
export { DEFAULT_SENSOR_BUFFER_CONFIG } from './types';

// Convenience factory functions
export function createSensorBuffer(config?: Partial<import('./types').SensorBufferConfig>) {
  return new SensorBuffer(config);
}

export function createMockTransport(shouldSucceed: boolean = true, delay: number = 100) {
  return new MockTransportAdapter(shouldSucceed, delay);
}

export function createHttpTransport(
  endpoint: string,
  options?: {
    headers?: Record<string, string>;
    timeout?: number;
    retryAttempts?: number;
    debug?: boolean;
  }
) {
  return new HttpTransportAdapter(endpoint, options);
}

export function createSupabaseTransport(
  supabaseClient: any,
  tableName?: string,
  debug?: boolean
) {
  return new SupabaseTransportAdapter(supabaseClient, tableName, debug);
}