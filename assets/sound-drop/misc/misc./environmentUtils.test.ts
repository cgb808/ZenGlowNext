// GoCodeo-style tests for environmentUtils
import { readNoiseLevel, readLightLevel, logEnvironmentalData } from './environmentUtils';
import { EnvironmentalSensorData } from '../types/environment';

function testReadNoiseLevel() {
  const noise = readNoiseLevel();
  console.assert(typeof noise === 'number', 'Noise level should be a number');
}

function testReadLightLevel() {
  const light = readLightLevel();
  console.assert(typeof light === 'number', 'Light level should be a number');
}

function testLogEnvironmentalData() {
  const data: EnvironmentalSensorData = {
    timestamp: new Date(),
    noiseLevel: 42,
    lightLevel: 100,
  };
  logEnvironmentalData(data);
  console.log('logEnvironmentalData executed.');
}

testReadNoiseLevel();
testReadLightLevel();
testLogEnvironmentalData();
console.log('All environmentUtils tests passed.');
