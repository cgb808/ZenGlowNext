/**
 * Tests for TransportAdapter implementations
 */

import {
  HttpTransportAdapter,
  SupabaseTransportAdapter,
  MockTransportAdapter,
} from '../TransportAdapter';
import { SensorReading } from '../types';

// Mock fetch for HttpTransportAdapter tests
global.fetch = jest.fn();

describe('TransportAdapter', () => {
  beforeEach(() => {
    jest.useRealTimers();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('HttpTransportAdapter', () => {
    let adapter: HttpTransportAdapter;
    const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

    beforeEach(() => {
      adapter = new HttpTransportAdapter('https://api.example.com/sensors', {
        debug: true,
        timeout: 5000,
        retryAttempts: 2,
      });
      mockFetch.mockClear();
    });

    it('should send batch successfully', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
      } as Response);

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(2);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/sensors',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ readings }),
        })
      );
    });

    it('should handle empty batch', async () => {
      const result = await adapter.sendBatch([]);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(0);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should handle HTTP errors with retries', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(false);
      expect(result.error).toContain('HTTP 500');
      expect(mockFetch).toHaveBeenCalledTimes(2); // Original + 1 retry
    });

    it('should handle network errors with retries', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      mockFetch.mockRejectedValue(new Error('Network error'));

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
      expect(mockFetch).toHaveBeenCalledTimes(2); // Original + 1 retry
    });

    it('should include custom headers', async () => {
      const adapterWithHeaders = new HttpTransportAdapter(
        'https://api.example.com/sensors',
        {
          headers: {
            'Authorization': 'Bearer token123',
            'X-Custom-Header': 'value',
          },
        }
      );

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
      } as Response);

      await adapterWithHeaders.sendBatch([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/sensors',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token123',
            'X-Custom-Header': 'value',
          }),
        })
      );
    });
  });

  describe('SupabaseTransportAdapter', () => {
    let adapter: SupabaseTransportAdapter;
    let mockSupabaseClient: any;

    beforeEach(() => {
      mockSupabaseClient = {
        from: jest.fn().mockReturnThis(),
        insert: jest.fn().mockResolvedValue({ error: null }),
      };

      adapter = new SupabaseTransportAdapter(
        mockSupabaseClient,
        'sensor_data',
        true
      );
    });

    it('should send batch successfully', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(2);
      expect(mockSupabaseClient.from).toHaveBeenCalledWith('sensor_data');
      expect(mockSupabaseClient.insert).toHaveBeenCalledWith([
        {
          sensor_type: 'temperature',
          value: 25.5,
          quality: 90,
          timestamp: new Date(1000).toISOString(),
          local_id: 1,
        },
        {
          sensor_type: 'humidity',
          value: 60.0,
          quality: 85,
          timestamp: new Date(2000).toISOString(),
          local_id: 2,
        },
      ]);
    });

    it('should handle empty batch', async () => {
      const result = await adapter.sendBatch([]);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(0);
      expect(mockSupabaseClient.from).not.toHaveBeenCalled();
    });

    it('should handle Supabase errors', async () => {
      mockSupabaseClient.insert.mockResolvedValue({
        error: { message: 'Database connection failed' },
      });

      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Database connection failed');
      expect(result.flushedCount).toBe(0);
    });

    it('should handle unexpected errors', async () => {
      mockSupabaseClient.from.mockImplementation(() => {
        throw new Error('Unexpected error');
      });

      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Unexpected error');
      expect(result.flushedCount).toBe(0);
    });
  });

  describe('MockTransportAdapter', () => {
    let adapter: MockTransportAdapter;

    beforeEach(() => {
      adapter = new MockTransportAdapter(true, 0, true); // No delay for faster tests
    });

    it('should send batch successfully when configured to succeed', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(2);
      expect(adapter.sentBatches).toHaveLength(1);
      expect(adapter.sentBatches[0]).toEqual(readings);
    });

    it('should fail when configured to fail', async () => {
      adapter.setShouldSucceed(false);

      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      const result = await adapter.sendBatch(readings);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Mock transport failure');
      expect(result.flushedCount).toBe(0);
      expect(adapter.sentBatches).toHaveLength(1); // Still records the attempt
    });

    it('should handle empty batch', async () => {
      const result = await adapter.sendBatch([]);

      expect(result.success).toBe(true);
      expect(result.flushedCount).toBe(0);
      expect(adapter.sentBatches).toHaveLength(1);
      expect(adapter.sentBatches[0]).toEqual([]);
    });

    it('should track multiple batches', async () => {
      const readings1: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      const readings2: SensorReading[] = [
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];

      await adapter.sendBatch(readings1);
      await adapter.sendBatch(readings2);

      expect(adapter.sentBatches).toHaveLength(2);
      expect(adapter.getTotalSentReadings()).toBe(2);
    });

    it('should reset properly', async () => {
      const readings: SensorReading[] = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];

      await adapter.sendBatch(readings);
      expect(adapter.sentBatches).toHaveLength(1);

      adapter.reset();
      expect(adapter.sentBatches).toHaveLength(0);
      expect(adapter.getTotalSentReadings()).toBe(0);
    });

    it('should simulate delay when configured', async () => {
      const delayAdapter = new MockTransportAdapter(true, 10); // Short delay
      const startTime = Date.now();
      
      await delayAdapter.sendBatch([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      const endTime = Date.now();
      expect(endTime - startTime).toBeGreaterThanOrEqual(5); // Allow some tolerance
    });
  });
});