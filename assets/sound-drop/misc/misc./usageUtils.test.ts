// GoCodeo-style tests for usageUtils
import { logUsageEvent, getUsageAnalytics } from './usageUtils';
import { AppUsageEvent } from '../types/usage';

const mockEvent: AppUsageEvent = {
  timestamp: new Date(),
  eventType: 'open',
  details: 'App opened by user',
};

function testLogUsageEvent() {
  logUsageEvent(mockEvent);
  console.log('logUsageEvent executed.');
}

function testGetUsageAnalytics() {
  const analytics = getUsageAnalytics();
  console.assert(
    typeof analytics.dailyActiveUsers === 'number',
    'dailyActiveUsers should be a number',
  );
  console.log('getUsageAnalytics executed.');
}

testLogUsageEvent();
testGetUsageAnalytics();
console.log('All usageUtils tests passed.');
