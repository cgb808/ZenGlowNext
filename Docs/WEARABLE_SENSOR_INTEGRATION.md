# Wearable Sensor Integration

ZenGlow's wearable sensor integration provides local buffering and reliable data synchronization for sensor data from wearable devices. The system uses SQLite for local storage and intelligent flush scheduling to ensure data persistence and optimal network usage.

## Architecture

The sensor system consists of three main components:

1. **SQLite Storage** (`src/sensors/storage/db.ts`) - Local database for buffering sensor readings
2. **Flush Scheduler** (`src/sensors/flushScheduler.ts`) - Intelligent scheduling of data synchronization
3. **Transport Adapter** (`src/sensors/transport.ts`) - Pluggable transport layer for sending data to server

## Quick Start

### Basic Usage

```typescript
import { sensorSystem } from '@/sensors';

// Initialize the sensor system
await sensorSystem.init();

// Record sensor data
await sensorSystem.recordReading({
  sensor_type: 'heart_rate',
  value: 72,
  unit: 'bpm',
  timestamp: Date.now(),
  device_id: 'wearable-001'
});

// Manually flush pending data (optional)
await sensorSystem.flush();

// Get system statistics
const stats = sensorSystem.getStats();
console.log(`Pending readings: ${stats.pendingReadings}`);

// Shutdown when done
await sensorSystem.shutdown();
```

### Advanced Configuration

```typescript
import { 
  createFlushScheduler, 
  createTransportAdapter,
  sensorDb 
} from '@/sensors';

// Custom flush scheduler configuration
const customScheduler = createFlushScheduler({
  intervalMs: 2 * 60 * 1000,    // Flush every 2 minutes
  batchThreshold: 100,          // Flush when 100+ readings pending
  enableAppResumeTrigger: true, // Flush when app becomes active
  enableIntervalTrigger: true,  // Enable time-based flushing
  enableBatchTrigger: true,     // Enable threshold-based flushing
});

// Custom transport adapter (for production HTTP endpoints)
const httpTransport = createTransportAdapter('http', {
  baseUrl: 'https://api.zenglow.com',
  apiKey: 'your-api-key'
});

// Initialize database directly for low-level operations
await sensorDb.init();

// Insert reading directly
const readingId = await sensorDb.insert({
  sensor_type: 'step_count',
  value: 8500,
  unit: 'steps',
  timestamp: Date.now(),
  device_id: 'wearable-001'
});

// Get pending readings
const pendingReadings = await sensorDb.getPending(50); // Limit to 50

// Mark readings as flushed after successful transmission
await sensorDb.markFlushed([readingId]);
```

## Sensor Data Schema

Sensor readings follow this structure:

```typescript
interface SensorReading {
  id?: number;           // Auto-generated primary key
  sensor_type: string;   // Type of sensor (e.g., 'heart_rate', 'step_count', 'sleep_quality')
  value: number;         // Sensor reading value
  unit: string;          // Unit of measurement (e.g., 'bpm', 'steps', 'score')
  timestamp: number;     // When the reading was taken (Unix timestamp)
  device_id: string;     // Unique identifier for the wearable device
  flushed: boolean;      // Whether reading has been sent to server
  created_at: number;    // When reading was stored locally (Unix timestamp)
}
```

### Supported Sensor Types

| Sensor Type | Unit | Description |
|-------------|------|-------------|
| `heart_rate` | `bpm` | Heart rate in beats per minute |
| `step_count` | `steps` | Daily step count |
| `sleep_quality` | `score` | Sleep quality score (0-100) |
| `activity_level` | `score` | Activity intensity score (0-100) |
| `stress_level` | `score` | Stress level indicator (0-100) |
| `oxygen_saturation` | `percent` | Blood oxygen saturation percentage |

## Flush Scheduling

The flush scheduler automatically synchronizes local data with the server using multiple triggers:

### Trigger Types

1. **App Resume** - Flushes data when the app becomes active
2. **Time Interval** - Flushes data at regular intervals (default: 5 minutes)  
3. **Batch Threshold** - Flushes data when pending readings exceed threshold (default: 50)

### Configuration Options

```typescript
interface FlushSchedulerConfig {
  intervalMs: number;              // Flush interval in milliseconds
  batchThreshold: number;          // Flush when this many readings pending
  transport?: TransportAdapter;    // Custom transport adapter
  enableAppResumeTrigger: boolean; // Enable flush on app resume
  enableIntervalTrigger: boolean;  // Enable interval-based flushing
  enableBatchTrigger: boolean;     // Enable batch threshold flushing
}
```

## Transport Adapters

### Stub Transport (Default)

The stub transport simulates successful data transmission for development and testing:

```typescript
import { stubTransport } from '@/sensors';

const result = await stubTransport.flush(pendingReadings);
// Always returns { success: true, flushedIds: [...] }
```

### HTTP Transport (Production)

For production deployments, use the HTTP transport adapter:

```typescript
import { createTransportAdapter } from '@/sensors';

const httpTransport = createTransportAdapter('http', {
  baseUrl: 'https://api.zenglow.com',
  apiKey: process.env.ZENGLOW_API_KEY
});

// Will POST data to: https://api.zenglow.com/api/sensor-data
```

### Custom Transport

Implement your own transport adapter:

```typescript
import { TransportAdapter, PendingReading, TransportResult } from '@/sensors';

class CustomTransport implements TransportAdapter {
  async flush(readings: PendingReading[]): Promise<TransportResult> {
    try {
      // Your custom transmission logic here
      const response = await yourCustomAPI.sendSensorData(readings);
      
      return {
        success: true,
        flushedIds: readings.map(r => r.id)
      };
    } catch (error) {
      return {
        success: false,
        flushedIds: [],
        error: error.message
      };
    }
  }
}
```

## Error Handling

The sensor system includes comprehensive error handling:

```typescript
try {
  await sensorSystem.init();
} catch (error) {
  console.error('Failed to initialize sensor system:', error);
  // Handle initialization failure
}

try {
  await sensorSystem.recordReading(reading);
} catch (error) {
  console.error('Failed to record sensor reading:', error);
  // Handle recording failure - data may be lost
}

// Check flush results
const flushSuccess = await sensorSystem.flush();
if (!flushSuccess) {
  console.warn('Flush failed - data will retry on next flush');
  // Data remains in local storage for retry
}
```

## Performance Considerations

### Batch Processing

The system is optimized for batch processing:

```typescript
// Efficient: Record multiple readings
const readings = [...]; // Array of sensor readings
for (const reading of readings) {
  await sensorSystem.recordReading(reading);
}

// Efficient: Single flush for all pending data
await sensorSystem.flush();
```

### Memory Management

- Old flushed readings are automatically cleaned up
- SQLite database uses efficient indexing
- Batch size limits prevent memory issues

```typescript
// Manual cleanup of old data (optional)
const deletedCount = await sensorDb.cleanupOldReadings(7); // 7 days
console.log(`Cleaned up ${deletedCount} old readings`);
```

### Network Optimization

- Automatic batching reduces network requests
- Retry logic handles temporary network failures
- App state triggers optimize for user behavior

## Monitoring and Statistics

Monitor system health with built-in statistics:

```typescript
const stats = sensorSystem.getStats();

console.log('Sensor System Statistics:', {
  totalFlushes: stats.totalFlushes,
  successfulFlushes: stats.successfulFlushes,
  failedFlushes: stats.failedFlushes,
  successRate: (stats.successfulFlushes / stats.totalFlushes) * 100,
  lastFlushTime: new Date(stats.lastFlushTime),
  pendingReadings: stats.pendingReadings
});
```

## Testing

The sensor system includes comprehensive test coverage:

```bash
# Run sensor system tests
npm test __tests__/sensors/

# Run with coverage
npm run test:coverage __tests__/sensors/
```

### Test Structure

- **Unit Tests** - Individual component testing with mocked dependencies
- **Integration Tests** - End-to-end workflow testing
- **Mock Adapters** - Configurable mocks for testing failure scenarios

### Example Test

```typescript
import { sensorSystem } from '@/sensors';

describe('Sensor Integration', () => {
  beforeEach(async () => {
    await sensorSystem.init();
  });

  afterEach(async () => {
    await sensorSystem.shutdown();
  });

  it('records and flushes sensor data', async () => {
    // Record test data
    const id = await sensorSystem.recordReading({
      sensor_type: 'heart_rate',
      value: 72,
      unit: 'bpm',
      timestamp: Date.now(),
      device_id: 'test-device'
    });

    expect(id).toBeGreaterThan(0);

    // Flush data
    const success = await sensorSystem.flush();
    expect(success).toBe(true);

    // Verify statistics
    const stats = sensorSystem.getStats();
    expect(stats.successfulFlushes).toBe(1);
  });
});
```

## Troubleshooting

### Common Issues

**Database not initialized**
```
Error: Database not initialized
```
Solution: Call `await sensorSystem.init()` before using the system.

**High memory usage**
Solution: Enable automatic cleanup or manually clean old data:
```typescript
await sensorDb.cleanupOldReadings(3); // Keep only 3 days of data
```

**Flush failures**
Solution: Check network connectivity and transport configuration:
```typescript
const stats = sensorSystem.getStats();
if (stats.failedFlushes > stats.successfulFlushes) {
  // Investigate transport configuration
}
```

### Debug Mode

Enable detailed logging for debugging:

```typescript
// Enable debug logging in transport
const debugTransport = createTransportAdapter('stub', {
  simulateNetworkDelay: true,
  delayMs: 1000,
  failureRate: 0.1 // 10% failure rate for testing
});
```

## Migration and Upgrades

### Database Schema Updates

The SQLite schema is versioned and includes automatic migration:

```sql
-- Current schema (v1)
CREATE TABLE sensor_readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sensor_type TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  device_id TEXT NOT NULL,
  flushed BOOLEAN DEFAULT FALSE,
  created_at INTEGER NOT NULL
);

CREATE INDEX idx_flushed ON sensor_readings(flushed);
CREATE INDEX idx_timestamp ON sensor_readings(timestamp);
```

### Data Export/Import

Export data for backup or migration:

```typescript
// Export pending readings
const pendingData = await sensorDb.getPending();
const exportData = JSON.stringify(pendingData, null, 2);

// Save to file or send to backup service
await FileSystem.writeAsStringAsync('sensor_backup.json', exportData);
```

## Security Considerations

- Local SQLite database is sandboxed to the app
- No sensitive data should be stored in sensor readings
- Transport layer should use HTTPS for production
- API keys should be stored securely (environment variables, secure storage)

```typescript
// Secure API key storage example
import { SecureStore } from 'expo-secure-store';

const apiKey = await SecureStore.getItemAsync('zenglow_api_key');
const transport = createTransportAdapter('http', {
  baseUrl: 'https://api.zenglow.com',
  apiKey: apiKey
});
```