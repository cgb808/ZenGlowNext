/**
 * =================================================================================
 * FLUSH SCHEDULER - Manages automatic flushing of sensor data
 * =================================================================================
 * Purpose: Automatically flush sensor readings based on various triggers
 * Features:
 * - Interval-based flushing
 * - App state change monitoring
 * - Batch size trigger
 * - Age-based trigger
 * - Manual flush capability
 * =================================================================================
 */

import { AppState, AppStateStatus } from 'react-native';
import { FlushConfig, TransportAdapter, SensorReading } from './types';
import { SensorDatabase } from './SensorDatabase';

export type FlushTrigger = 'interval' | 'batch_size' | 'max_age' | 'app_state' | 'manual';

export interface FlushEvent {
  trigger: FlushTrigger;
  readingsCount: number;
  success: boolean;
  error?: string;
  timestamp: number;
}

export class FlushScheduler {
  private config: FlushConfig;
  private database: SensorDatabase;
  private transport: TransportAdapter | null;
  private debug: boolean;

  private intervalId: NodeJS.Timeout | null = null;
  private appStateSubscription: any = null;
  private isRunning = false;
  private isFlushInProgress = false;

  // Event listeners
  private flushEventListeners: ((event: FlushEvent) => void)[] = [];

  constructor(
    config: FlushConfig,
    database: SensorDatabase,
    transport: TransportAdapter | null = null,
    debug: boolean = false
  ) {
    this.config = config;
    this.database = database;
    this.transport = transport;
    this.debug = debug;
  }

  /**
   * Start the flush scheduler
   */
  start(): void {
    if (this.isRunning) {
      if (this.debug) {
        console.log('[FlushScheduler] Already running');
      }
      return;
    }

    if (this.debug) {
      console.log('[FlushScheduler] Starting with config:', this.config);
    }

    this.isRunning = true;

    // Start interval-based flushing
    this.startIntervalFlushing();

    // Start app state monitoring
    if (this.config.enableAppStateFlush) {
      this.startAppStateMonitoring();
    }
  }

  /**
   * Stop the flush scheduler
   */
  stop(): void {
    if (!this.isRunning) {
      return;
    }

    if (this.debug) {
      console.log('[FlushScheduler] Stopping');
    }

    this.isRunning = false;

    // Clear interval
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    // Remove app state listener
    if (this.appStateSubscription) {
      this.appStateSubscription.remove();
      this.appStateSubscription = null;
    }
  }

  /**
   * Manually trigger a flush
   */
  async flush(): Promise<FlushEvent> {
    return this.performFlush('manual');
  }

  /**
   * Check if flush is needed based on batch size or age
   */
  async checkAndFlush(): Promise<FlushEvent | null> {
    try {
      const pendingReadings = await this.database.getPending();
      
      if (pendingReadings.length === 0) {
        return null;
      }

      // Check batch size trigger
      if (pendingReadings.length >= this.config.batchSize) {
        if (this.debug) {
          console.log('[FlushScheduler] Triggering flush due to batch size:', pendingReadings.length);
        }
        return this.performFlush('batch_size');
      }

      // Check age trigger
      const oldestReading = pendingReadings[0]; // Readings are ordered by timestamp
      if (oldestReading && (Date.now() - oldestReading.ts) > this.config.maxAge) {
        if (this.debug) {
          console.log('[FlushScheduler] Triggering flush due to age:', Date.now() - oldestReading.ts, 'ms');
        }
        return this.performFlush('max_age');
      }

      return null;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (this.debug) {
        console.error('[FlushScheduler] Error in checkAndFlush:', errorMessage);
      }
      return {
        trigger: 'manual',
        readingsCount: 0,
        success: false,
        error: errorMessage,
        timestamp: Date.now(),
      };
    }
  }

  /**
   * Set transport adapter
   */
  setTransport(transport: TransportAdapter | null): void {
    this.transport = transport;
    if (this.debug) {
      console.log('[FlushScheduler] Transport adapter updated');
    }
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<FlushConfig>): void {
    this.config = { ...this.config, ...config };
    
    if (this.debug) {
      console.log('[FlushScheduler] Configuration updated:', this.config);
    }

    // Restart if running to apply new config
    if (this.isRunning) {
      this.stop();
      this.start();
    }
  }

  /**
   * Add flush event listener
   */
  addFlushEventListener(listener: (event: FlushEvent) => void): void {
    this.flushEventListeners.push(listener);
  }

  /**
   * Remove flush event listener
   */
  removeFlushEventListener(listener: (event: FlushEvent) => void): void {
    const index = this.flushEventListeners.indexOf(listener);
    if (index > -1) {
      this.flushEventListeners.splice(index, 1);
    }
  }

  /**
   * Get current status
   */
  getStatus(): {
    isRunning: boolean;
    isFlushInProgress: boolean;
    config: FlushConfig;
  } {
    return {
      isRunning: this.isRunning,
      isFlushInProgress: this.isFlushInProgress,
      config: this.config,
    };
  }

  /**
   * Start interval-based flushing
   */
  private startIntervalFlushing(): void {
    if (this.config.flushInterval <= 0) {
      return;
    }

    this.intervalId = setInterval(async () => {
      if (!this.isFlushInProgress) {
        const event = await this.performFlush('interval');
        if (this.debug && event.readingsCount > 0) {
          console.log('[FlushScheduler] Interval flush completed:', event);
        }
      }
    }, this.config.flushInterval);
  }

  /**
   * Start app state monitoring
   */
  private startAppStateMonitoring(): void {
    this.appStateSubscription = AppState.addEventListener(
      'change',
      this.handleAppStateChange.bind(this)
    );
  }

  /**
   * Handle app state changes
   */
  private async handleAppStateChange(nextAppState: AppStateStatus): Promise<void> {
    if (this.debug) {
      console.log('[FlushScheduler] App state changed to:', nextAppState);
    }

    // Flush when app goes to background
    if (nextAppState === 'background' || nextAppState === 'inactive') {
      if (!this.isFlushInProgress) {
        const event = await this.performFlush('app_state');
        if (this.debug && event.readingsCount > 0) {
          console.log('[FlushScheduler] App state flush completed:', event);
        }
      }
    }
  }

  /**
   * Perform the actual flush operation
   */
  private async performFlush(trigger: FlushTrigger): Promise<FlushEvent> {
    if (this.isFlushInProgress) {
      if (this.debug) {
        console.log('[FlushScheduler] Flush already in progress, skipping');
      }
      return {
        trigger,
        readingsCount: 0,
        success: false,
        error: 'Flush already in progress',
        timestamp: Date.now(),
      };
    }

    this.isFlushInProgress = true;

    try {
      // Get pending readings
      const pendingReadings = await this.database.getPending();
      
      if (pendingReadings.length === 0) {
        const event: FlushEvent = {
          trigger,
          readingsCount: 0,
          success: true,
          timestamp: Date.now(),
        };
        this.notifyFlushEventListeners(event);
        return event;
      }

      if (!this.transport) {
        if (this.debug) {
          console.warn('[FlushScheduler] No transport adapter configured');
        }
        const event: FlushEvent = {
          trigger,
          readingsCount: pendingReadings.length,
          success: false,
          error: 'No transport adapter configured',
          timestamp: Date.now(),
        };
        this.notifyFlushEventListeners(event);
        return event;
      }

      // Send readings
      const result = await this.transport.sendBatch(pendingReadings);

      if (result.success) {
        // Mark readings as flushed
        const ids = pendingReadings
          .filter(reading => reading.id !== undefined)
          .map(reading => reading.id!);
        
        if (ids.length > 0) {
          await this.database.markFlushed(ids);
        }

        if (this.debug) {
          console.log('[FlushScheduler] Successfully flushed', result.flushedCount, 'readings');
        }
      }

      const event: FlushEvent = {
        trigger,
        readingsCount: pendingReadings.length,
        success: result.success,
        error: result.error,
        timestamp: Date.now(),
      };

      this.notifyFlushEventListeners(event);
      return event;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (this.debug) {
        console.error('[FlushScheduler] Flush error:', errorMessage);
      }

      const event: FlushEvent = {
        trigger,
        readingsCount: 0,
        success: false,
        error: errorMessage,
        timestamp: Date.now(),
      };

      this.notifyFlushEventListeners(event);
      return event;

    } finally {
      this.isFlushInProgress = false;
    }
  }

  /**
   * Notify all flush event listeners
   */
  private notifyFlushEventListeners(event: FlushEvent): void {
    this.flushEventListeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        if (this.debug) {
          console.error('[FlushScheduler] Error in flush event listener:', error);
        }
      }
    });
  }
}