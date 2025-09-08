/**
 * Flush Scheduler for Wearable Sensor Data
 * 
 * Manages automatic flushing of sensor data with multiple triggers:
 * - App resume (foreground state)
 * - Time interval (configurable)
 * - Batch threshold (number of pending readings)
 */

import { AppState, AppStateStatus } from 'react-native';
import { sensorDb } from './storage/db';
import { TransportAdapter, stubTransport } from './transport';

export interface FlushSchedulerConfig {
  intervalMs: number;        // Flush interval in milliseconds
  batchThreshold: number;    // Flush when this many readings are pending
  transport?: TransportAdapter; // Transport adapter (defaults to stub)
  enableAppResumeTrigger: boolean; // Enable flush on app resume
  enableIntervalTrigger: boolean;  // Enable interval-based flushing
  enableBatchTrigger: boolean;     // Enable batch threshold flushing
}

export interface FlushStats {
  totalFlushes: number;
  successfulFlushes: number;
  failedFlushes: number;
  lastFlushTime: number | null;
  pendingReadings: number;
}

class FlushScheduler {
  private config: FlushSchedulerConfig;
  private transport: TransportAdapter;
  private intervalTimer: ReturnType<typeof setInterval> | null = null;
  private appStateSubscription: any = null;
  private isRunning = false;
  private stats: FlushStats = {
    totalFlushes: 0,
    successfulFlushes: 0,
    failedFlushes: 0,
    lastFlushTime: null,
    pendingReadings: 0
  };

  constructor(config: Partial<FlushSchedulerConfig> = {}) {
    this.config = {
      intervalMs: 5 * 60 * 1000, // 5 minutes default
      batchThreshold: 50,         // 50 readings default
      transport: stubTransport,
      enableAppResumeTrigger: true,
      enableIntervalTrigger: true,
      enableBatchTrigger: true,
      ...config
    };
    
    this.transport = this.config.transport!;
  }

  /**
   * Start the flush scheduler
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn('[FlushScheduler] Already running');
      return;
    }

    this.isRunning = true;
    console.log('[FlushScheduler] Starting with config:', this.config);

    // Initialize database if not already initialized
    try {
      await sensorDb.init();
    } catch (error) {
      console.error('[FlushScheduler] Failed to initialize database:', error);
      throw error;
    }

    // Set up app state listener for resume trigger
    if (this.config.enableAppResumeTrigger) {
      this.setupAppStateListener();
    }

    // Set up interval timer
    if (this.config.enableIntervalTrigger) {
      this.setupIntervalTimer();
    }

    // Initial flush to clear any pending data
    await this.flush();
  }

  /**
   * Stop the flush scheduler
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    console.log('[FlushScheduler] Stopping');
    this.isRunning = false;

    // Clear interval timer
    if (this.intervalTimer) {
      clearInterval(this.intervalTimer);
      this.intervalTimer = null;
    }

    // Remove app state listener
    if (this.appStateSubscription) {
      this.appStateSubscription.remove();
      this.appStateSubscription = null;
    }

    // Final flush before stopping
    await this.flush();
  }

  /**
   * Manually trigger a flush
   */
  async flush(): Promise<boolean> {
    if (!this.isRunning) {
      console.warn('[FlushScheduler] Not running, skipping flush');
      return false;
    }

    try {
      const pendingReadings = await sensorDb.getPending();
      
      if (pendingReadings.length === 0) {
        console.log('[FlushScheduler] No pending readings to flush');
        this.stats.pendingReadings = 0;
        return true;
      }

      console.log(`[FlushScheduler] Flushing ${pendingReadings.length} pending readings`);
      this.stats.totalFlushes++;

      const result = await this.transport.flush(pendingReadings);
      
      if (result.success && result.flushedIds.length > 0) {
        await sensorDb.markFlushed(result.flushedIds);
        this.stats.successfulFlushes++;
        this.stats.lastFlushTime = Date.now();
        
        console.log(`[FlushScheduler] Successfully flushed ${result.flushedIds.length} readings`);
        
        // Update pending count
        this.stats.pendingReadings = await sensorDb.getPendingCount();
        
        return true;
      } else {
        this.stats.failedFlushes++;
        console.error('[FlushScheduler] Flush failed:', result.error);
        return false;
      }
    } catch (error) {
      this.stats.failedFlushes++;
      console.error('[FlushScheduler] Flush error:', error);
      return false;
    }
  }

  /**
   * Check if batch threshold is reached and flush if needed
   */
  async checkBatchThreshold(): Promise<void> {
    if (!this.config.enableBatchTrigger || !this.isRunning) {
      return;
    }

    try {
      const pendingCount = await sensorDb.getPendingCount();
      this.stats.pendingReadings = pendingCount;

      if (pendingCount >= this.config.batchThreshold) {
        console.log(`[FlushScheduler] Batch threshold reached (${pendingCount}/${this.config.batchThreshold}), triggering flush`);
        await this.flush();
      }
    } catch (error) {
      console.error('[FlushScheduler] Error checking batch threshold:', error);
    }
  }

  /**
   * Get current statistics
   */
  getStats(): FlushStats {
    return { ...this.stats };
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<FlushSchedulerConfig>): void {
    const wasRunning = this.isRunning;
    
    if (wasRunning) {
      this.stop();
    }

    this.config = { ...this.config, ...newConfig };
    
    if (newConfig.transport) {
      this.transport = newConfig.transport;
    }

    if (wasRunning) {
      this.start();
    }
  }

  private setupAppStateListener(): void {
    this.appStateSubscription = AppState.addEventListener('change', this.handleAppStateChange.bind(this));
  }

  private async handleAppStateChange(nextAppState: AppStateStatus): Promise<void> {
    if (nextAppState === 'active') {
      console.log('[FlushScheduler] App resumed, triggering flush');
      await this.flush();
    }
  }

  private setupIntervalTimer(): void {
    this.intervalTimer = setInterval(async () => {
      console.log('[FlushScheduler] Interval timer triggered');
      await this.flush();
    }, this.config.intervalMs);
  }
}

// Export singleton instance
export const flushScheduler = new FlushScheduler();

// Export factory for creating custom schedulers
export const createFlushScheduler = (config?: Partial<FlushSchedulerConfig>): FlushScheduler => {
  return new FlushScheduler(config);
};