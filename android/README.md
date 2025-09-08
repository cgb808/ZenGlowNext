# ZenGlow Android Heart Rate Monitor

This Android module provides comprehensive heart rate monitoring capabilities for the ZenGlow wellness app, with support for both built-in sensors and Samsung Galaxy Watch integration.

## Features

### Core Functionality

- **Real-time Heart Rate Monitoring**: Continuous heart rate tracking from device sensors
- **Galaxy Watch Integration**: Full Samsung Galaxy Watch support via Accessory SDK
- **On-Body Detection**: Automatic detection when sensor is properly positioned
- **Data Validation**: Real-time validation of heart rate readings with timeout handling
- **Background Monitoring**: Persistent monitoring with foreground service

### Samsung Health Integration

- **Native Samsung Health Support**: Direct integration with Samsung Health platform
- **Automatic Data Sync**: Seamless synchronization of heart rate data
- **Exercise Session Recording**: Context-aware exercise and meditation session tracking
- **Permission Management**: Comprehensive permission handling for health data access

### Multi-Platform Export

- **Samsung Health**: Native integration with full permission support
- **Apple Health**: HealthKit XML export for cross-platform compatibility
- **Google Fit**: Direct API integration for Google's health platform
- **Garmin Connect**: FIT file export for Garmin ecosystem compatibility

### Device Compatibility

- **Built-in Sensors**: Support for native Android heart rate sensors
- **Galaxy Watch Series**: Watch, Watch Active, Watch4/5/6 series support
- **Bluetooth Connectivity**: Robust wireless connection management
- **Multi-Device Fallback**: Automatic fallback between device and watch sensors

## Architecture

### Service Components

- `HeartRateActivity`: Main UI for heart rate monitoring
- `SamsungHealthService`: Samsung Health SDK integration
- `GalaxyWatchService`: Galaxy Watch communication and data handling
- `HeartRateMonitorService`: Core monitoring service with statistics
- `HealthDataExportService`: Multi-platform health data export

### Data Management

- **Real-time Processing**: Live heart rate data processing and validation
- **Statistical Analysis**: Heart rate variability (HRV) calculation
- **Historical Data**: Persistent storage of heart rate readings
- **Export Formats**: CSV, XML, JSON, and FIT file format support

## Permissions

### Required Permissions

```xml
<!-- Core heart rate monitoring -->
<uses-permission android:name="android.permission.BODY_SENSORS" />
<uses-permission android:name="android.permission.BODY_SENSORS_BACKGROUND" />

<!-- Galaxy Watch connectivity -->
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
<uses-permission android:name="com.samsung.wearable.permission.REMOTE_CONTROL" />

<!-- Samsung Health integration -->
<uses-permission android:name="com.samsung.android.providers.context.permission.WRITE_USE_APP_FEATURE_SURVEY" />

<!-- Data export -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

## Setup Instructions

### 1. Samsung Health SDK Setup

1. Register application at Samsung Health Developer Portal
2. Obtain API credentials and configure in app
3. Add Samsung Health SDK dependency to build.gradle
4. Configure health data permissions in manifest

### 2. Galaxy Watch SDK Setup

1. Download Samsung Accessory SDK from Samsung Developer Portal
2. Place SDK JAR files in `app/libs/` directory
3. Configure Accessory SDK permissions and services
4. Set up watch app communication protocol

### 3. Health Platform API Configuration

1. **Google Fit**: Configure OAuth 2.0 credentials in Google Cloud Console
2. **Apple Health**: Set up HealthKit export capability
3. **Garmin Connect**: Configure Garmin Connect IQ developer credentials

## Usage Examples

### Basic Heart Rate Monitoring

```java
HeartRateActivity activity = new HeartRateActivity();
activity.startHeartRateMonitoring();

// Monitor real-time readings
activity.setHeartRateCallback(new HeartRateCallback() {
    @Override
    public void onHeartRateReceived(int heartRate, long timestamp) {
        Log.d("HeartRate", "Current: " + heartRate + " BPM");
    }
});
```

### Samsung Health Integration

```java
SamsungHealthService healthService = new SamsungHealthService(context);
healthService.startMonitoring();

// Record heart rate data
healthService.recordHeartRate(75, System.currentTimeMillis());

// Record exercise session
healthService.recordExerciseSession("meditation", startTime, endTime, avgHeartRate, maxHeartRate);
```

### Galaxy Watch Connection

```java
GalaxyWatchService watchService = new GalaxyWatchService(context);
watchService.setHeartRateCallback(callback);
watchService.startHeartRateMonitoring();

// Check connection status
if (watchService.isConnected()) {
    int latestRate = watchService.getLatestHeartRate();
}
```

### Health Data Export

```java
HealthDataExportService exportService = new HealthDataExportService(context);

// Export to multiple platforms
exportService.exportToSamsungHealth();
exportService.exportToAppleHealth();
exportService.exportToGoogleFit();
exportService.exportToGarmin();
```

## Data Formats

### Heart Rate Reading Structure

```java
public class HeartRateReading {
    public final int heartRate;      // BPM value
    public final long timestamp;     // Unix timestamp
    public final String source;      // "device" or "watch"
}
```

### Statistical Analysis

```java
public class HeartRateStatistics {
    public final int currentHeartRate;
    public final double averageHeartRate;
    public final int minHeartRate;
    public final int maxHeartRate;
    public final double heartRateVariability;  // RMSSD calculation
    public final long totalReadings;
}
```

## Integration with ZenGlow

### Wellness Model Integration

The heart rate monitor integrates with ZenGlow's TensorFlow Lite wellness prediction model:

```java
// Heart rate data feeds into wellness model
int currentHeartRate = monitorService.getCurrentHeartRate();
double heartRateVariability = monitorService.getHeartRateVariability();

// Combined with other wellness metrics for AI prediction
WellnessMetrics metrics = new WellnessMetrics(currentHeartRate, heartRateVariability, ...);
float wellnessScore = wellnessModel.predict(metrics);
```

### Parent Dashboard Connection

Heart rate data is available to the parent dashboard for child wellness monitoring:

```java
// Real-time heart rate sharing
parentDashboard.updateChildHeartRate(childId, currentHeartRate, timestamp);

// Wellness alerts based on heart rate patterns
if (heartRate > childMaxThreshold || heartRateVariability < minThreshold) {
    parentDashboard.sendWellnessAlert(childId, "Heart rate attention needed");
}
```

## Security and Privacy

### Data Protection

- All heart rate data is encrypted at rest and in transit
- Local processing minimizes cloud data exposure
- User consent required for all health platform integrations
- HIPAA-compliant data handling where applicable

### Permission Management

- Runtime permission requests with clear explanations
- Granular permission control for each health platform
- Easy opt-out mechanisms for data sharing
- Transparent data usage policies

## Troubleshooting

### Common Issues

1. **Sensor Not Detected**: Ensure device has heart rate sensor or Galaxy Watch is connected
2. **Permission Denied**: Check all required permissions are granted in system settings
3. **Galaxy Watch Connection Failed**: Verify Bluetooth is enabled and watch is paired
4. **Samsung Health Sync Issues**: Confirm Samsung Health app is installed and permissions granted
5. **Export Failures**: Verify API credentials and network connectivity

### Debug Logging

Enable debug logging for detailed troubleshooting:

```java
Log.setProperty("zenglow.heartrate.debug", "true");
```

## Dependencies

### Core Android

- androidx.appcompat:appcompat:1.6.1
- com.google.android.material:material:1.11.0
- androidx.cardview:cardview:1.0.0

### Samsung SDKs

- com.samsung.android:health-data:1.5.0
- samsung-android-sdk-accessory.jar
- samsung-android-provider-accessory.jar

### Health Platform Integration

- com.google.android.gms:play-services-fitness:21.1.0
- com.squareup.retrofit2:retrofit:2.9.0
- com.google.code.gson:gson:2.10.1

## Version History

### v1.0.0 (Current)

- Initial implementation with full Samsung Galaxy Watch support
- Samsung Health SDK integration
- Multi-platform health data export (Samsung Health, Apple Health, Google Fit, Garmin)
- Real-time heart rate monitoring with on-body detection
- Heart rate variability calculation
- Comprehensive statistics and data export capabilities

## Support

For technical support and integration questions:

- Review Samsung Health SDK documentation
- Check Samsung Galaxy Watch Accessory SDK guides
- Consult Google Fit API documentation
- Reference Garmin Connect IQ developer resources

## License

This module is part of the ZenGlow wellness application and follows the project's overall licensing terms.
