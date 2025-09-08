/**
 * =================================================================================
 * SENSOR DATABASE - SQLite database management for sensor readings
 * =================================================================================
 * Purpose: Low-level SQLite operations for sensor data buffering
 * Features:
 * - SQLite database initialization and management
 * - CRUD operations for sensor readings
 * - Transaction support for batch operations
 * - Automatic schema migration
 * =================================================================================
 */

import * as SQLite from 'expo-sqlite';
import { SensorReading, SensorReadingInput } from './types';

export class SensorDatabase {
  private db: SQLite.SQLiteDatabase | null = null;
  private isInitialized = false;
  private databaseName: string;
  private debug: boolean;

  constructor(databaseName: string = 'sensor_buffer.db', debug: boolean = false) {
    this.databaseName = databaseName;
    this.debug = debug;
  }

  /**
   * Initialize the database and create tables
   */
  async initialize(): Promise<boolean> {
    try {
      if (this.isInitialized && this.db) {
        return true;
      }

      if (this.debug) {
        console.log('[SensorDatabase] Initializing database:', this.databaseName);
      }

      this.db = await SQLite.openDatabaseAsync(this.databaseName);
      
      // Create sensor_readings table
      await this.db.execAsync(`
        CREATE TABLE IF NOT EXISTS sensor_readings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sensor_type TEXT NOT NULL,
          value REAL NOT NULL,
          quality INTEGER NOT NULL,
          ts INTEGER NOT NULL,
          flushed INTEGER DEFAULT 0
        );
      `);

      // Create indexes for better performance
      await this.db.execAsync(`
        CREATE INDEX IF NOT EXISTS idx_sensor_readings_ts ON sensor_readings(ts);
        CREATE INDEX IF NOT EXISTS idx_sensor_readings_flushed ON sensor_readings(flushed);
        CREATE INDEX IF NOT EXISTS idx_sensor_readings_type ON sensor_readings(sensor_type);
      `);

      this.isInitialized = true;
      
      if (this.debug) {
        console.log('[SensorDatabase] Database initialized successfully');
      }

      return true;
    } catch (error) {
      console.error('[SensorDatabase] Failed to initialize database:', error);
      return false;
    }
  }

  /**
   * Insert a single sensor reading
   */
  async insertReading(reading: SensorReadingInput): Promise<boolean> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      const ts = reading.ts || Date.now();
      
      const result = await this.db.runAsync(
        'INSERT INTO sensor_readings (sensor_type, value, quality, ts, flushed) VALUES (?, ?, ?, ?, 0)',
        [reading.sensor_type, reading.value, reading.quality, ts]
      );

      if (this.debug) {
        console.log('[SensorDatabase] Inserted reading:', result.lastInsertRowId);
      }

      return result.changes > 0;
    } catch (error) {
      console.error('[SensorDatabase] Failed to insert reading:', error);
      return false;
    }
  }

  /**
   * Insert multiple sensor readings in a transaction
   */
  async insertBatch(readings: SensorReadingInput[]): Promise<boolean> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      if (readings.length === 0) {
        return true;
      }

      await this.db.withTransactionAsync(async () => {
        for (const reading of readings) {
          const ts = reading.ts || Date.now();
          await this.db!.runAsync(
            'INSERT INTO sensor_readings (sensor_type, value, quality, ts, flushed) VALUES (?, ?, ?, ?, 0)',
            [reading.sensor_type, reading.value, reading.quality, ts]
          );
        }
      });

      if (this.debug) {
        console.log('[SensorDatabase] Inserted batch of', readings.length, 'readings');
      }

      return true;
    } catch (error) {
      console.error('[SensorDatabase] Failed to insert batch:', error);
      return false;
    }
  }

  /**
   * Get pending (unflushed) sensor readings
   */
  async getPending(limit?: number): Promise<SensorReading[]> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      const query = limit
        ? 'SELECT * FROM sensor_readings WHERE flushed = 0 ORDER BY ts ASC LIMIT ?'
        : 'SELECT * FROM sensor_readings WHERE flushed = 0 ORDER BY ts ASC';
      
      const params = limit ? [limit] : [];
      
      const result = await this.db.getAllAsync(query, params);
      
      if (this.debug) {
        console.log('[SensorDatabase] Retrieved', result.length, 'pending readings');
      }

      return result as SensorReading[];
    } catch (error) {
      console.error('[SensorDatabase] Failed to get pending readings:', error);
      return [];
    }
  }

  /**
   * Mark readings as flushed
   */
  async markFlushed(ids: number[]): Promise<boolean> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      if (ids.length === 0) {
        return true;
      }

      const placeholders = ids.map(() => '?').join(',');
      const result = await this.db.runAsync(
        `UPDATE sensor_readings SET flushed = 1 WHERE id IN (${placeholders})`,
        ids
      );

      if (this.debug) {
        console.log('[SensorDatabase] Marked', result.changes, 'readings as flushed');
      }

      return result.changes > 0;
    } catch (error) {
      console.error('[SensorDatabase] Failed to mark readings as flushed:', error);
      return false;
    }
  }

  /**
   * Purge old readings
   */
  async purge(beforeTs?: number): Promise<number> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      let query: string;
      let params: any[];

      if (beforeTs) {
        // Purge readings older than specified timestamp
        query = 'DELETE FROM sensor_readings WHERE ts < ?';
        params = [beforeTs];
      } else {
        // Purge all flushed readings
        query = 'DELETE FROM sensor_readings WHERE flushed = 1';
        params = [];
      }

      const result = await this.db.runAsync(query, params);

      if (this.debug) {
        console.log('[SensorDatabase] Purged', result.changes, 'readings');
      }

      return result.changes;
    } catch (error) {
      console.error('[SensorDatabase] Failed to purge readings:', error);
      return 0;
    }
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<{
    total: number;
    pending: number;
    flushed: number;
    oldestTs?: number;
    newestTs?: number;
  }> {
    try {
      if (!this.db) {
        throw new Error('Database not initialized');
      }

      const [totalResult, pendingResult, flushedResult, timestampResult] = await Promise.all([
        this.db.getFirstAsync('SELECT COUNT(*) as count FROM sensor_readings'),
        this.db.getFirstAsync('SELECT COUNT(*) as count FROM sensor_readings WHERE flushed = 0'),
        this.db.getFirstAsync('SELECT COUNT(*) as count FROM sensor_readings WHERE flushed = 1'),
        this.db.getFirstAsync('SELECT MIN(ts) as oldest, MAX(ts) as newest FROM sensor_readings'),
      ]);

      return {
        total: (totalResult as any)?.count || 0,
        pending: (pendingResult as any)?.count || 0,
        flushed: (flushedResult as any)?.count || 0,
        oldestTs: (timestampResult as any)?.oldest || undefined,
        newestTs: (timestampResult as any)?.newest || undefined,
      };
    } catch (error) {
      console.error('[SensorDatabase] Failed to get stats:', error);
      return {
        total: 0,
        pending: 0,
        flushed: 0,
      };
    }
  }

  /**
   * Close the database connection
   */
  async close(): Promise<void> {
    try {
      if (this.db) {
        await this.db.closeAsync();
        this.db = null;
        this.isInitialized = false;
        
        if (this.debug) {
          console.log('[SensorDatabase] Database closed');
        }
      }
    } catch (error) {
      console.error('[SensorDatabase] Failed to close database:', error);
    }
  }

  /**
   * Check if database is initialized
   */
  isReady(): boolean {
    return this.isInitialized && this.db !== null;
  }
}