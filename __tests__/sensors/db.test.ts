/**
 * Unit tests for SQLite sensor database
 */

import { type SensorReading } from '../../src/sensors/storage/db';

// Import after mocking
import { sensorDb } from '../../src/sensors/storage/db';

// Mock expo-sqlite
const mockDb = {
  execAsync: jest.fn(),
  runAsync: jest.fn(),
  getAllAsync: jest.fn(),
  getFirstAsync: jest.fn(),
  closeAsync: jest.fn(),
};

jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn(() => Promise.resolve(mockDb)),
}));

describe('SensorDatabase', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the database state
    (sensorDb as any).db = null;
  });

  afterEach(async () => {
    try {
      await sensorDb.close();
    } catch (e) {
      // Ignore errors during cleanup
    }
  });

  describe('init', () => {
    it('initializes database and creates schema', async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);

      await sensorDb.init();

      expect(mockDb.execAsync).toHaveBeenCalledWith(
        expect.stringContaining('CREATE TABLE IF NOT EXISTS sensor_readings')
      );
    });

    it('throws error if initialization fails', async () => {
      const error = new Error('DB init failed');
      mockDb.execAsync.mockRejectedValueOnce(error);

      await expect(sensorDb.init()).rejects.toThrow('Failed to initialize sensor database');
    });
  });

  describe('insert', () => {
    beforeEach(async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);
      await sensorDb.init();
    });

    it('inserts sensor reading successfully', async () => {
      const reading = {
        sensor_type: 'heart_rate',
        value: 72,
        unit: 'bpm',
        timestamp: 1625097600000,
        device_id: 'wearable-001'
      };

      mockDb.runAsync.mockResolvedValueOnce({ lastInsertRowId: 1 });

      const id = await sensorDb.insert(reading);

      expect(id).toBe(1);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO sensor_readings'),
        [reading.sensor_type, reading.value, reading.unit, reading.timestamp, reading.device_id, expect.any(Number)]
      );
    });

    it('throws error if database not initialized', async () => {
      (sensorDb as any).db = null; // Force uninitialized state

      const reading = {
        sensor_type: 'heart_rate',
        value: 72,
        unit: 'bpm',
        timestamp: 1625097600000,
        device_id: 'wearable-001'
      };

      await expect(sensorDb.insert(reading)).rejects.toThrow('Database not initialized');
    });

    it('throws error if insert fails', async () => {
      const reading = {
        sensor_type: 'heart_rate',
        value: 72,
        unit: 'bpm',
        timestamp: 1625097600000,
        device_id: 'wearable-001'
      };

      const error = new Error('Insert failed');
      mockDb.runAsync.mockRejectedValueOnce(error);

      await expect(sensorDb.insert(reading)).rejects.toThrow('Failed to insert sensor reading');
    });
  });

  describe('getPending', () => {
    beforeEach(async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);
      await sensorDb.init();
    });

    it('returns pending readings without limit', async () => {
      const mockRows = [
        {
          id: 1,
          sensor_type: 'heart_rate',
          value: 72,
          unit: 'bpm',
          timestamp: 1625097600000,
          device_id: 'wearable-001',
          flushed: false,
          created_at: 1625097600000
        }
      ];

      mockDb.getAllAsync.mockResolvedValueOnce(mockRows);

      const result = await sensorDb.getPending();

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual(expect.objectContaining({
        id: 1,
        sensor_type: 'heart_rate',
        value: 72,
        unit: 'bpm',
        flushed: false
      }));
    });

    it('returns pending readings with limit', async () => {
      mockDb.getAllAsync.mockResolvedValueOnce([]);

      await sensorDb.getPending(10);

      expect(mockDb.getAllAsync).toHaveBeenCalledWith(
        expect.stringContaining('LIMIT 10')
      );
    });

    it('throws error if database not initialized', async () => {
      (sensorDb as any).db = null; // Force uninitialized state

      await expect(sensorDb.getPending()).rejects.toThrow('Database not initialized');
    });

    it('throws error if query fails', async () => {
      const error = new Error('Query failed');
      mockDb.getAllAsync.mockRejectedValueOnce(error);

      await expect(sensorDb.getPending()).rejects.toThrow('Failed to get pending readings');
    });
  });

  describe('markFlushed', () => {
    beforeEach(async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);
      await sensorDb.init();
    });

    it('marks readings as flushed', async () => {
      const ids = [1, 2, 3];
      mockDb.runAsync.mockResolvedValueOnce({ changes: 3 });

      await sensorDb.markFlushed(ids);

      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'UPDATE sensor_readings SET flushed = TRUE WHERE id IN (?,?,?)',
        ids
      );
    });

    it('handles empty ids array', async () => {
      await sensorDb.markFlushed([]);

      expect(mockDb.runAsync).not.toHaveBeenCalled();
    });

    it('throws error if database not initialized', async () => {
      (sensorDb as any).db = null; // Force uninitialized state

      await expect(sensorDb.markFlushed([1, 2])).rejects.toThrow('Database not initialized');
    });

    it('throws error if update fails', async () => {
      const error = new Error('Update failed');
      mockDb.runAsync.mockRejectedValueOnce(error);

      await expect(sensorDb.markFlushed([1, 2])).rejects.toThrow('Failed to mark readings as flushed');
    });
  });

  describe('getPendingCount', () => {
    beforeEach(async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);
      await sensorDb.init();
    });

    it('returns pending count', async () => {
      mockDb.getFirstAsync.mockResolvedValueOnce({ count: 5 });

      const count = await sensorDb.getPendingCount();

      expect(count).toBe(5);
      expect(mockDb.getFirstAsync).toHaveBeenCalledWith(
        'SELECT COUNT(*) as count FROM sensor_readings WHERE flushed = FALSE'
      );
    });

    it('throws error if database not initialized', async () => {
      (sensorDb as any).db = null; // Force uninitialized state

      await expect(sensorDb.getPendingCount()).rejects.toThrow('Database not initialized');
    });
  });

  describe('cleanupOldReadings', () => {
    beforeEach(async () => {
      mockDb.execAsync.mockResolvedValueOnce(undefined);
      await sensorDb.init();
    });

    it('cleans up old flushed readings', async () => {
      mockDb.runAsync.mockResolvedValueOnce({ changes: 10 });

      const deletedCount = await sensorDb.cleanupOldReadings(7);

      expect(deletedCount).toBe(10);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'DELETE FROM sensor_readings WHERE flushed = TRUE AND created_at < ?',
        [expect.any(Number)]
      );
    });

    it('throws error if database not initialized', async () => {
      (sensorDb as any).db = null; // Force uninitialized state

      await expect(sensorDb.cleanupOldReadings()).rejects.toThrow('Database not initialized');
    });
  });
});