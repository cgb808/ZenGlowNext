/**
 * Wearable Sensor Data Buffering System
 * 
 * Main entry point for sensor data collection, storage and flushing.
 * 
 * Usage:
 * ```ts
 * import { sensorSystem } from '@/sensors';
 * 
 * // Initialize the system
 * await sensorSystem.init();
 * 
 * // Record sensor data
 * await sensorSystem.recordReading({
 *   sensor_type: 'heart_rate',
 *   value: 72,
 *   unit: 'bpm',
 *   timestamp: Date.now(),
 *   device_id: 'wearable-001'
 * });
 * 
 * // Manually flush if needed
 * await sensorSystem.flush();
 * ```
 */

import { sensorDb, type SensorReading } from './storage/db';
import { flushScheduler } from './flushScheduler';

export { sensorDb, type SensorReading, type PendingReading } from './storage/db';
export { 
  stubTransport, 
  createTransportAdapter, 
  type TransportAdapter, 
  type TransportResult 
} from './transport';
export { 
  flushScheduler, 
  createFlushScheduler, 
  type FlushSchedulerConfig, 
  type FlushStats 
} from './flushScheduler';

/**
 * High-level sensor system API
 */
class SensorSystem {
  private initialized = false;

  /**
   * Initialize the sensor system
   */
  async init(): Promise<void> {
    if (this.initialized) {
      console.warn('[SensorSystem] Already initialized');
      return;
    }

    try {
      // Initialize database
      await sensorDb.init();
      
      // Start flush scheduler
      await flushScheduler.start();
      
      this.initialized = true;
      console.log('[SensorSystem] Initialized successfully');
    } catch (error) {
      console.error('[SensorSystem] Failed to initialize:', error);
      throw error;
    }
  }

  /**
   * Record a new sensor reading
   */
  async recordReading(reading: Omit<SensorReading, 'id' | 'flushed' | 'created_at'>): Promise<number> {
    if (!this.initialized) {
      throw new Error('Sensor system not initialized. Call init() first.');
    }

    try {
      const id = await sensorDb.insert(reading);
      
      // Check if batch threshold is reached
      await flushScheduler.checkBatchThreshold();
      
      return id;
    } catch (error) {
      console.error('[SensorSystem] Failed to record reading:', error);
      throw error;
    }
  }

  /**
   * Manually flush pending readings
   */
  async flush(): Promise<boolean> {
    if (!this.initialized) {
      throw new Error('Sensor system not initialized. Call init() first.');
    }

    return await flushScheduler.flush();
  }

  /**
   * Get system statistics
   */
  getStats() {
    return flushScheduler.getStats();
  }

  /**
   * Shutdown the sensor system
   */
  async shutdown(): Promise<void> {
    if (!this.initialized) {
      return;
    }

    try {
      await flushScheduler.stop();
      await sensorDb.close();
      
      this.initialized = false;
      console.log('[SensorSystem] Shutdown successfully');
    } catch (error) {
      console.error('[SensorSystem] Error during shutdown:', error);
      throw error;
    }
  }

  /**
   * Check if system is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const sensorSystem = new SensorSystem();