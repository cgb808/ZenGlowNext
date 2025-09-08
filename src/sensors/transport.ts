/**
 * Stub Transport Adapter for Sensor Data
 * 
 * Simulates successful transport of sensor data to server.
 * In future, this will be replaced with actual HTTP POST to backend.
 */

import { PendingReading } from './storage/db';

export interface TransportResult {
  success: boolean;
  flushedIds: number[];
  error?: string;
}

export interface TransportAdapter {
  flush(readings: PendingReading[]): Promise<TransportResult>;
}

/**
 * Stub implementation that always returns success
 * Future: Replace with actual HTTP transport
 */
class StubTransportAdapter implements TransportAdapter {
  private simulateNetworkDelay: boolean;
  private delayMs: number;
  private failureRate: number;

  constructor(options: {
    simulateNetworkDelay?: boolean;
    delayMs?: number;
    failureRate?: number;
  } = {}) {
    this.simulateNetworkDelay = options.simulateNetworkDelay ?? true;
    this.delayMs = options.delayMs ?? 100;
    this.failureRate = options.failureRate ?? 0; // 0% failure rate by default
  }

  /**
   * Stub flush implementation
   * Always returns success after optional simulated delay
   */
  async flush(readings: PendingReading[]): Promise<TransportResult> {
    // Simulate network delay if enabled
    if (this.simulateNetworkDelay && this.delayMs > 0) {
      await this.delay(this.delayMs);
    }

    // Simulate occasional failures for testing
    if (this.failureRate > 0 && Math.random() < this.failureRate) {
      return {
        success: false,
        flushedIds: [],
        error: 'Simulated network failure'
      };
    }

    // Log for debugging (in production, this would be actual HTTP POST)
    console.log(`[StubTransport] Successfully "flushed" ${readings.length} sensor readings:`, {
      readings: readings.map(r => ({
        id: r.id,
        sensor_type: r.sensor_type,
        value: r.value,
        timestamp: r.timestamp
      }))
    });

    // Return success with all reading IDs
    return {
      success: true,
      flushedIds: readings.map(r => r.id)
    };
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Production HTTP Transport Adapter (Future Implementation)
 * This would replace StubTransportAdapter in production
 */
class HttpTransportAdapter implements TransportAdapter {
  private baseUrl: string;
  private apiKey?: string;

  constructor(baseUrl: string, apiKey?: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async flush(readings: PendingReading[]): Promise<TransportResult> {
    try {
      // Future implementation would POST to actual server
      const response = await fetch(`${this.baseUrl}/api/sensor-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({ readings })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        success: true,
        flushedIds: readings.map(r => r.id)
      };
    } catch (error) {
      return {
        success: false,
        flushedIds: [],
        error: error instanceof Error ? error.message : 'Unknown transport error'
      };
    }
  }
}

// Export default stub implementation
export const stubTransport = new StubTransportAdapter();

// Export factory for creating transport adapters
export const createTransportAdapter = (type: 'stub' | 'http', options?: any): TransportAdapter => {
  switch (type) {
    case 'stub':
      return new StubTransportAdapter(options);
    case 'http':
      return new HttpTransportAdapter(options.baseUrl, options.apiKey);
    default:
      throw new Error(`Unknown transport type: ${type}`);
  }
};