/**
 * =================================================================================
 * SENSOR BUFFER - Main sensor data buffering service
 * =================================================================================
 * Purpose: High-level API for local sensor data buffering with automatic flushing
 * Features:
 * - SQLite-based local storage
 * - Automatic flush scheduling
 * - Transport adapter integration
 * - Comprehensive monitoring and statistics
 * =================================================================================
 */

import {
  SensorReading,
  SensorReadingInput,
  SensorBufferConfig,
  TransportAdapter,
  BufferStats,
  DEFAULT_SENSOR_BUFFER_CONFIG,
} from './types';
import { SensorDatabase } from './SensorDatabase';
import { FlushScheduler, FlushEvent } from './FlushScheduler';

export class SensorBuffer {
  private config: SensorBufferConfig;
  private database: SensorDatabase;
  private flushScheduler: FlushScheduler;
  private isInitialized = false;

  constructor(config: Partial<SensorBufferConfig> = {}) {
    this.config = { ...DEFAULT_SENSOR_BUFFER_CONFIG, ...config };
    
    this.database = new SensorDatabase(
      this.config.databaseName,
      this.config.debug
    );

    this.flushScheduler = new FlushScheduler(
      this.config.flush,
      this.database,
      this.config.transport,
      this.config.debug
    );

    if (this.config.debug) {
      console.log('[SensorBuffer] Created with config:', this.config);
    }
  }

  /**
   * Initialize the sensor buffer
   */
  async initialize(): Promise<boolean> {
    try {
      if (this.isInitialized) {
        if (this.config.debug) {
          console.log('[SensorBuffer] Already initialized');
        }
        return true;
      }

      if (this.config.debug) {
        console.log('[SensorBuffer] Initializing...');
      }

      // Initialize database
      const dbInitialized = await this.database.initialize();
      if (!dbInitialized) {
        throw new Error('Failed to initialize database');
      }

      // Start flush scheduler
      this.flushScheduler.start();

      this.isInitialized = true;

      if (this.config.debug) {
        console.log('[SensorBuffer] Initialized successfully');
      }

      return true;
    } catch (error) {
      console.error('[SensorBuffer] Failed to initialize:', error);
      return false;
    }
  }

  /**
   * Shutdown the sensor buffer
   */
  async shutdown(): Promise<void> {
    try {
      if (this.config.debug) {
        console.log('[SensorBuffer] Shutting down...');
      }

      // Stop flush scheduler
      this.flushScheduler.stop();

      // Perform final flush
      if (this.config.transport) {
        await this.flushScheduler.flush();
      }

      // Close database
      await this.database.close();

      this.isInitialized = false;

      if (this.config.debug) {
        console.log('[SensorBuffer] Shutdown complete');
      }
    } catch (error) {
      console.error('[SensorBuffer] Error during shutdown:', error);
    }
  }

  /**
   * Insert a single sensor reading
   */
  async insertReading(reading: SensorReadingInput): Promise<boolean> {
    if (!this.isInitialized) {
      console.error('[SensorBuffer] Not initialized');
      return false;
    }

    try {
      const success = await this.database.insertReading(reading);
      
      if (success && this.config.debug) {
        console.log('[SensorBuffer] Inserted reading:', reading.sensor_type);
      }

      // Check if flush is needed
      if (success) {
        this.flushScheduler.checkAndFlush().catch(error => {
          if (this.config.debug) {
            console.error('[SensorBuffer] Error in checkAndFlush:', error);
          }
        });
      }

      return success;
    } catch (error) {
      console.error('[SensorBuffer] Failed to insert reading:', error);
      return false;
    }
  }

  /**
   * Insert multiple sensor readings in a batch
   */
  async insertBatch(readings: SensorReadingInput[]): Promise<boolean> {
    if (!this.isInitialized) {
      console.error('[SensorBuffer] Not initialized');
      return false;
    }

    if (readings.length === 0) {
      return true;
    }

    try {
      const success = await this.database.insertBatch(readings);
      
      if (success && this.config.debug) {
        console.log('[SensorBuffer] Inserted batch of', readings.length, 'readings');
      }

      // Check if flush is needed
      if (success) {
        this.flushScheduler.checkAndFlush().catch(error => {
          if (this.config.debug) {
            console.error('[SensorBuffer] Error in checkAndFlush:', error);
          }
        });
      }

      return success;
    } catch (error) {
      console.error('[SensorBuffer] Failed to insert batch:', error);
      return false;
    }
  }

  /**
   * Get pending (unflushed) sensor readings
   */
  async getPending(limit?: number): Promise<SensorReading[]> {
    if (!this.isInitialized) {
      console.error('[SensorBuffer] Not initialized');
      return [];
    }

    try {
      return await this.database.getPending(limit);
    } catch (error) {
      console.error('[SensorBuffer] Failed to get pending readings:', error);
      return [];
    }
  }

  /**
   * Mark readings as flushed
   */
  async markFlushed(ids: number[]): Promise<boolean> {
    if (!this.isInitialized) {
      console.error('[SensorBuffer] Not initialized');
      return false;
    }

    try {
      return await this.database.markFlushed(ids);
    } catch (error) {
      console.error('[SensorBuffer] Failed to mark readings as flushed:', error);
      return false;
    }
  }

  /**
   * Purge old readings
   */
  async purge(beforeTs?: number): Promise<number> {
    if (!this.isInitialized) {
      console.error('[SensorBuffer] Not initialized');
      return 0;
    }

    try {
      return await this.database.purge(beforeTs);
    } catch (error) {
      console.error('[SensorBuffer] Failed to purge readings:', error);
      return 0;
    }
  }

  /**
   * Manually trigger a flush
   */
  async flush(): Promise<FlushEvent> {
    if (!this.isInitialized) {
      return {
        trigger: 'manual',
        readingsCount: 0,
        success: false,
        error: 'Not initialized',
        timestamp: Date.now(),
      };
    }

    return this.flushScheduler.flush();
  }

  /**
   * Get buffer statistics
   */
  async getStats(): Promise<BufferStats> {
    if (!this.isInitialized) {
      return {
        totalReadings: 0,
        pendingReadings: 0,
        flushedReadings: 0,
      };
    }

    try {
      const dbStats = await this.database.getStats();
      return {
        totalReadings: dbStats.total,
        pendingReadings: dbStats.pending,
        flushedReadings: dbStats.flushed,
        oldestReading: dbStats.oldestTs,
        newestReading: dbStats.newestTs,
      };
    } catch (error) {
      console.error('[SensorBuffer] Failed to get stats:', error);
      return {
        totalReadings: 0,
        pendingReadings: 0,
        flushedReadings: 0,
      };
    }
  }

  /**
   * Set transport adapter
   */
  setTransport(transport: TransportAdapter | null): void {
    this.config.transport = transport;
    this.flushScheduler.setTransport(transport);
    
    if (this.config.debug) {
      console.log('[SensorBuffer] Transport adapter updated');
    }
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<SensorBufferConfig>): void {
    this.config = { ...this.config, ...config };
    
    if (config.flush) {
      this.flushScheduler.updateConfig(config.flush);
    }

    if (config.transport !== undefined) {
      this.setTransport(config.transport);
    }
    
    if (this.config.debug) {
      console.log('[SensorBuffer] Configuration updated:', this.config);
    }
  }

  /**
   * Add flush event listener
   */
  addFlushEventListener(listener: (event: FlushEvent) => void): void {
    this.flushScheduler.addFlushEventListener(listener);
  }

  /**
   * Remove flush event listener
   */
  removeFlushEventListener(listener: (event: FlushEvent) => void): void {
    this.flushScheduler.removeFlushEventListener(listener);
  }

  /**
   * Get current status
   */
  getStatus(): {
    isInitialized: boolean;
    schedulerStatus: {
      isRunning: boolean;
      isFlushInProgress: boolean;
    };
    databaseReady: boolean;
    hasTransport: boolean;
  } {
    const schedulerStatus = this.flushScheduler.getStatus();
    
    return {
      isInitialized: this.isInitialized,
      schedulerStatus: {
        isRunning: schedulerStatus.isRunning,
        isFlushInProgress: schedulerStatus.isFlushInProgress,
      },
      databaseReady: this.database.isReady(),
      hasTransport: this.config.transport !== null && this.config.transport !== undefined,
    };
  }

  /**
   * Check if the sensor buffer is ready for use
   */
  isReady(): boolean {
    return this.isInitialized && this.database.isReady();
  }
}