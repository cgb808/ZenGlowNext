/**
 * SQLite Database for Wearable Sensor Data Buffering
 * 
 * Provides local storage for sensor readings with CRUD operations:
 * - insert: Store new sensor readings 
 * - getPending: Retrieve readings pending flush
 * - markFlushed: Mark readings as successfully flushed
 */

import * as SQLite from 'expo-sqlite';

export interface SensorReading {
  id?: number;
  sensor_type: string;
  value: number;
  unit: string;
  timestamp: number;
  device_id: string;
  flushed: boolean;
  created_at: number;
}

export interface PendingReading extends SensorReading {
  id: number;
}

class SensorDatabase {
  private db: SQLite.SQLiteDatabase | null = null;

  /**
   * Initialize SQLite database and create schema
   */
  async init(): Promise<void> {
    try {
      this.db = await SQLite.openDatabaseAsync('sensor_readings.db');
      
      await this.db.execAsync(`
        CREATE TABLE IF NOT EXISTS sensor_readings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sensor_type TEXT NOT NULL,
          value REAL NOT NULL,
          unit TEXT NOT NULL,
          timestamp INTEGER NOT NULL,
          device_id TEXT NOT NULL,
          flushed BOOLEAN DEFAULT FALSE,
          created_at INTEGER NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_flushed ON sensor_readings(flushed);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp);
      `);
    } catch (error) {
      throw new Error(`Failed to initialize sensor database: ${error}`);
    }
  }

  /**
   * Insert a new sensor reading
   */
  async insert(reading: Omit<SensorReading, 'id' | 'flushed' | 'created_at'>): Promise<number> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const result = await this.db.runAsync(
        `INSERT INTO sensor_readings (sensor_type, value, unit, timestamp, device_id, flushed, created_at)
         VALUES (?, ?, ?, ?, ?, FALSE, ?)`,
        [reading.sensor_type, reading.value, reading.unit, reading.timestamp, reading.device_id, Date.now()]
      );
      
      return result.lastInsertRowId;
    } catch (error) {
      throw new Error(`Failed to insert sensor reading: ${error}`);
    }
  }

  /**
   * Get pending sensor readings (not yet flushed)
   */
  async getPending(limit?: number): Promise<PendingReading[]> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const query = `
        SELECT * FROM sensor_readings 
        WHERE flushed = FALSE 
        ORDER BY created_at ASC
        ${limit ? `LIMIT ${limit}` : ''}
      `;
      
      const result = await this.db.getAllAsync(query);
      
      return result.map((row: any) => ({
        id: row.id as number,
        sensor_type: row.sensor_type as string,
        value: row.value as number,
        unit: row.unit as string,
        timestamp: row.timestamp as number,
        device_id: row.device_id as string,
        flushed: Boolean(row.flushed),
        created_at: row.created_at as number,
      }));
    } catch (error) {
      throw new Error(`Failed to get pending readings: ${error}`);
    }
  }

  /**
   * Mark readings as flushed (successfully sent to server)
   */
  async markFlushed(ids: number[]): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    if (ids.length === 0) {
      return;
    }

    try {
      const placeholders = ids.map(() => '?').join(',');
      await this.db.runAsync(
        `UPDATE sensor_readings SET flushed = TRUE WHERE id IN (${placeholders})`,
        ids
      );
    } catch (error) {
      throw new Error(`Failed to mark readings as flushed: ${error}`);
    }
  }

  /**
   * Get count of pending readings
   */
  async getPendingCount(): Promise<number> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const result = await this.db.getFirstAsync(
        'SELECT COUNT(*) as count FROM sensor_readings WHERE flushed = FALSE'
      ) as { count: number };
      
      return result.count;
    } catch (error) {
      throw new Error(`Failed to get pending count: ${error}`);
    }
  }

  /**
   * Clean up old flushed readings (optional maintenance)
   */
  async cleanupOldReadings(olderThanDays: number = 7): Promise<number> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const cutoffTime = Date.now() - (olderThanDays * 24 * 60 * 60 * 1000);
      const result = await this.db.runAsync(
        'DELETE FROM sensor_readings WHERE flushed = TRUE AND created_at < ?',
        [cutoffTime]
      );
      
      return result.changes;
    } catch (error) {
      throw new Error(`Failed to cleanup old readings: ${error}`);
    }
  }

  /**
   * Close database connection
   */
  async close(): Promise<void> {
    if (this.db) {
      await this.db.closeAsync();
      this.db = null;
    }
  }
}

// Export singleton instance
export const sensorDb = new SensorDatabase();