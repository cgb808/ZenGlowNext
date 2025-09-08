/**
 * =================================================================================
 * TRANSPORT ADAPTER - Interface and implementations for sending sensor data
 * =================================================================================
 * Purpose: Abstraction layer for sending sensor readings to remote services
 * Features:
 * - Transport adapter interface
 * - HTTP transport implementation
 * - Mock transport for testing
 * - Configurable retry logic
 * =================================================================================
 */

import { TransportAdapter, TransportResult, SensorReading } from './types';

/**
 * HTTP Transport Adapter - sends data via HTTP POST
 */
export class HttpTransportAdapter implements TransportAdapter {
  private endpoint: string;
  private headers: Record<string, string>;
  private timeout: number;
  private retryAttempts: number;
  private debug: boolean;

  constructor(
    endpoint: string,
    options: {
      headers?: Record<string, string>;
      timeout?: number;
      retryAttempts?: number;
      debug?: boolean;
    } = {}
  ) {
    this.endpoint = endpoint;
    this.headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    this.timeout = options.timeout || 10000; // 10 seconds
    this.retryAttempts = options.retryAttempts || 3;
    this.debug = options.debug || false;
  }

  async sendBatch(readings: SensorReading[]): Promise<TransportResult> {
    if (readings.length === 0) {
      return { success: true, flushedCount: 0 };
    }

    let lastError: string | undefined;

    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        if (this.debug) {
          console.log(`[HttpTransportAdapter] Sending batch (attempt ${attempt}/${this.retryAttempts}):`, readings.length, 'readings');
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(this.endpoint, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({ readings }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          if (this.debug) {
            console.log('[HttpTransportAdapter] Batch sent successfully');
          }
          return { success: true, flushedCount: readings.length };
        } else {
          lastError = `HTTP ${response.status}: ${response.statusText}`;
          if (this.debug) {
            console.warn(`[HttpTransportAdapter] HTTP error:`, lastError);
          }
        }
      } catch (error) {
        lastError = error instanceof Error ? error.message : 'Unknown error';
        if (this.debug) {
          console.warn(`[HttpTransportAdapter] Network error:`, lastError);
        }
      }

      // Wait before retry (exponential backoff)
      if (attempt < this.retryAttempts) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    return {
      success: false,
      error: lastError || 'Failed to send batch after retries',
      flushedCount: 0,
    };
  }
}

/**
 * Supabase Transport Adapter - sends data to Supabase
 */
export class SupabaseTransportAdapter implements TransportAdapter {
  private supabaseClient: any;
  private tableName: string;
  private debug: boolean;

  constructor(
    supabaseClient: any,
    tableName: string = 'sensor_readings',
    debug: boolean = false
  ) {
    this.supabaseClient = supabaseClient;
    this.tableName = tableName;
    this.debug = debug;
  }

  async sendBatch(readings: SensorReading[]): Promise<TransportResult> {
    if (readings.length === 0) {
      return { success: true, flushedCount: 0 };
    }

    try {
      if (this.debug) {
        console.log('[SupabaseTransportAdapter] Sending batch:', readings.length, 'readings');
      }

      // Convert readings to format expected by Supabase
      const supabaseReadings = readings.map(reading => ({
        sensor_type: reading.sensor_type,
        value: reading.value,
        quality: reading.quality,
        timestamp: new Date(reading.ts).toISOString(),
        local_id: reading.id,
      }));

      const { error } = await this.supabaseClient
        .from(this.tableName)
        .insert(supabaseReadings);

      if (error) {
        if (this.debug) {
          console.error('[SupabaseTransportAdapter] Supabase error:', error);
        }
        return {
          success: false,
          error: error.message,
          flushedCount: 0,
        };
      }

      if (this.debug) {
        console.log('[SupabaseTransportAdapter] Batch sent successfully');
      }

      return { success: true, flushedCount: readings.length };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (this.debug) {
        console.error('[SupabaseTransportAdapter] Unexpected error:', errorMessage);
      }
      return {
        success: false,
        error: errorMessage,
        flushedCount: 0,
      };
    }
  }
}

/**
 * Mock Transport Adapter - for testing and development
 */
export class MockTransportAdapter implements TransportAdapter {
  private shouldSucceed: boolean;
  private delay: number;
  private debug: boolean;
  public sentBatches: SensorReading[][] = [];

  constructor(
    shouldSucceed: boolean = true,
    delay: number = 100,
    debug: boolean = false
  ) {
    this.shouldSucceed = shouldSucceed;
    this.delay = delay;
    this.debug = debug;
  }

  async sendBatch(readings: SensorReading[]): Promise<TransportResult> {
    if (this.delay > 0) {
      await new Promise(resolve => setTimeout(resolve, this.delay));
    }

    if (this.debug) {
      console.log('[MockTransportAdapter] Sending batch:', readings.length, 'readings');
    }

    this.sentBatches.push([...readings]);

    if (this.shouldSucceed) {
      return { success: true, flushedCount: readings.length };
    } else {
      return {
        success: false,
        error: 'Mock transport failure',
        flushedCount: 0,
      };
    }
  }

  /**
   * Test utility methods
   */
  reset(): void {
    this.sentBatches = [];
  }

  setShouldSucceed(succeed: boolean): void {
    this.shouldSucceed = succeed;
  }

  getTotalSentReadings(): number {
    return this.sentBatches.reduce((total, batch) => total + batch.length, 0);
  }
}