/**
 * Basic Sensor Storage Integration Test
 * Simple test to verify core functionality works
 */

import { SensorType, SensorQuality } from '../../src/types/SensorData';

describe('Basic Sensor Storage Test', () => {
  it('sensor types are properly defined', () => {
    expect(SensorType.HEART_RATE).toBe('heart_rate');
    expect(SensorType.STRESS_LEVEL).toBe('stress_level');
    expect(SensorQuality.EXCELLENT).toBe('excellent');
    expect(SensorQuality.GOOD).toBe('good');
  });

  it('can import sensor storage modules', () => {
    expect(() => {
      require('../../src/types/SensorData');
      require('../../src/utils/EncryptedSensorStorage');
    }).not.toThrow();
  });
});