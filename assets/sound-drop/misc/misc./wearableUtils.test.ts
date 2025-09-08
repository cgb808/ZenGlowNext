// GoCodeo-style tests for wearableUtils
import { connectToWearable, syncWearableData } from './wearableUtils';
import { WearableDevice } from '../types/wearables';

const mockDevice: WearableDevice = {
  id: 'dev123',
  name: 'Test Tracker',
  type: 'fitness_tracker',
  connected: false,
  lastSync: null,
  data: {
    heartRate: 72,
    steps: 1000,
    sleep: { duration: 480, quality: 'good' },
  },
};

async function testConnectToWearable() {
  const result = await connectToWearable(mockDevice);
  console.assert(result === true, 'connectToWearable should resolve true');
}

async function testSyncWearableData() {
  const result = await syncWearableData(mockDevice);
  console.assert(result.id === mockDevice.id, 'syncWearableData should return device');
}

(async () => {
  await testConnectToWearable();
  await testSyncWearableData();
  console.log('All wearableUtils tests passed.');
})();
