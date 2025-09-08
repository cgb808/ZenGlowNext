/**
 * Tests for SensorDatabase class
 */

import { SensorDatabase } from '../SensorDatabase';
import { SensorReadingInput } from '../types';

// Mock expo-sqlite
jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn(),
}));

describe('SensorDatabase', () => {
  let database: SensorDatabase;
  let mockDb: any;

  beforeEach(() => {
    // Create mock database
    mockDb = {
      execAsync: jest.fn().mockResolvedValue(undefined),
      runAsync: jest.fn().mockResolvedValue({ changes: 1, lastInsertRowId: 1 }),
      getAllAsync: jest.fn().mockResolvedValue([]),
      getFirstAsync: jest.fn().mockResolvedValue({ count: 0 }),
      withTransactionAsync: jest.fn().mockImplementation(async (callback) => {
        await callback();
      }),
      closeAsync: jest.fn().mockResolvedValue(undefined),
    };

    // Mock openDatabaseAsync to return our mock
    const { openDatabaseAsync } = require('expo-sqlite');
    openDatabaseAsync.mockResolvedValue(mockDb);

    database = new SensorDatabase('test.db', true);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('initialize', () => {
    it('should initialize database successfully', async () => {
      const result = await database.initialize();

      expect(result).toBe(true);
      expect(mockDb.execAsync).toHaveBeenCalledWith(expect.stringContaining('CREATE TABLE IF NOT EXISTS sensor_readings'));
      expect(mockDb.execAsync).toHaveBeenCalledWith(expect.stringContaining('CREATE INDEX'));
    });

    it('should handle initialization errors', async () => {
      mockDb.execAsync.mockRejectedValue(new Error('Database error'));

      const result = await database.initialize();

      expect(result).toBe(false);
    });

    it('should not initialize twice', async () => {
      await database.initialize();
      mockDb.execAsync.mockClear();

      const result = await database.initialize();

      expect(result).toBe(true);
      expect(mockDb.execAsync).not.toHaveBeenCalled();
    });
  });

  describe('insertReading', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should insert a reading successfully', async () => {
      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
        ts: 1234567890000,
      };

      const result = await database.insertReading(reading);

      expect(result).toBe(true);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'INSERT INTO sensor_readings (sensor_type, value, quality, ts, flushed) VALUES (?, ?, ?, ?, 0)',
        ['temperature', 25.5, 90, 1234567890000]
      );
    });

    it('should use current timestamp if not provided', async () => {
      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      };

      const now = Date.now();
      jest.spyOn(Date, 'now').mockReturnValue(now);

      const result = await database.insertReading(reading);

      expect(result).toBe(true);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        expect.any(String),
        ['temperature', 25.5, 90, now]
      );

      jest.restoreAllMocks();
    });

    it('should handle insert errors', async () => {
      mockDb.runAsync.mockRejectedValue(new Error('Insert error'));

      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      };

      const result = await database.insertReading(reading);

      expect(result).toBe(false);
    });
  });

  describe('insertBatch', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should insert multiple readings in a transaction', async () => {
      const readings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000 },
        { sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000 },
      ];

      const result = await database.insertBatch(readings);

      expect(result).toBe(true);
      expect(mockDb.withTransactionAsync).toHaveBeenCalled();
    });

    it('should handle empty batch', async () => {
      const result = await database.insertBatch([]);

      expect(result).toBe(true);
      expect(mockDb.withTransactionAsync).not.toHaveBeenCalled();
    });

    it('should handle batch insert errors', async () => {
      mockDb.withTransactionAsync.mockRejectedValue(new Error('Transaction error'));

      const readings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
      ];

      const result = await database.insertBatch(readings);

      expect(result).toBe(false);
    });
  });

  describe('getPending', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should get pending readings without limit', async () => {
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];
      mockDb.getAllAsync.mockResolvedValue(mockReadings);

      const result = await database.getPending();

      expect(result).toEqual(mockReadings);
      expect(mockDb.getAllAsync).toHaveBeenCalledWith(
        'SELECT * FROM sensor_readings WHERE flushed = 0 ORDER BY ts ASC',
        []
      );
    });

    it('should get pending readings with limit', async () => {
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      mockDb.getAllAsync.mockResolvedValue(mockReadings);

      const result = await database.getPending(10);

      expect(result).toEqual(mockReadings);
      expect(mockDb.getAllAsync).toHaveBeenCalledWith(
        'SELECT * FROM sensor_readings WHERE flushed = 0 ORDER BY ts ASC LIMIT ?',
        [10]
      );
    });

    it('should handle get pending errors', async () => {
      mockDb.getAllAsync.mockRejectedValue(new Error('Query error'));

      const result = await database.getPending();

      expect(result).toEqual([]);
    });
  });

  describe('markFlushed', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should mark readings as flushed', async () => {
      const ids = [1, 2, 3];

      const result = await database.markFlushed(ids);

      expect(result).toBe(true);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'UPDATE sensor_readings SET flushed = 1 WHERE id IN (?,?,?)',
        [1, 2, 3]
      );
    });

    it('should handle empty ids array', async () => {
      const result = await database.markFlushed([]);

      expect(result).toBe(true);
      expect(mockDb.runAsync).not.toHaveBeenCalled();
    });

    it('should handle mark flushed errors', async () => {
      mockDb.runAsync.mockRejectedValue(new Error('Update error'));

      const result = await database.markFlushed([1, 2, 3]);

      expect(result).toBe(false);
    });
  });

  describe('purge', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should purge readings older than timestamp', async () => {
      mockDb.runAsync.mockResolvedValue({ changes: 5 });

      const result = await database.purge(1000000);

      expect(result).toBe(5);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'DELETE FROM sensor_readings WHERE ts < ?',
        [1000000]
      );
    });

    it('should purge all flushed readings when no timestamp provided', async () => {
      mockDb.runAsync.mockResolvedValue({ changes: 3 });

      const result = await database.purge();

      expect(result).toBe(3);
      expect(mockDb.runAsync).toHaveBeenCalledWith(
        'DELETE FROM sensor_readings WHERE flushed = 1',
        []
      );
    });

    it('should handle purge errors', async () => {
      mockDb.runAsync.mockRejectedValue(new Error('Delete error'));

      const result = await database.purge();

      expect(result).toBe(0);
    });
  });

  describe('getStats', () => {
    beforeEach(async () => {
      await database.initialize();
    });

    it('should get database statistics', async () => {
      mockDb.getFirstAsync
        .mockResolvedValueOnce({ count: 100 }) // total
        .mockResolvedValueOnce({ count: 20 })  // pending
        .mockResolvedValueOnce({ count: 80 })  // flushed
        .mockResolvedValueOnce({ oldest: 1000, newest: 5000 }); // timestamps

      const result = await database.getStats();

      expect(result).toEqual({
        total: 100,
        pending: 20,
        flushed: 80,
        oldestTs: 1000,
        newestTs: 5000,
      });
    });

    it('should handle stats query errors', async () => {
      mockDb.getFirstAsync.mockRejectedValue(new Error('Query error'));

      const result = await database.getStats();

      expect(result).toEqual({
        total: 0,
        pending: 0,
        flushed: 0,
      });
    });
  });

  describe('close', () => {
    it('should close database connection', async () => {
      await database.initialize();

      await database.close();

      expect(mockDb.closeAsync).toHaveBeenCalled();
      expect(database.isReady()).toBe(false);
    });

    it('should handle close errors', async () => {
      await database.initialize();
      mockDb.closeAsync.mockRejectedValue(new Error('Close error'));

      await database.close();

      // Should not throw error
      expect(mockDb.closeAsync).toHaveBeenCalled();
    });
  });

  describe('isReady', () => {
    it('should return false when not initialized', () => {
      expect(database.isReady()).toBe(false);
    });

    it('should return true when initialized', async () => {
      await database.initialize();

      expect(database.isReady()).toBe(true);
    });
  });
});