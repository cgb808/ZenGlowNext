package com.zenglow.heartrate;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.util.Log;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

public class HeartRateMonitorService extends Service {
    private static final String TAG = "HeartRateMonitor";
    private static final int MAX_READINGS = 1000; // Keep last 1000 readings
    
    private final IBinder binder = new HeartRateMonitorBinder();
    private final ConcurrentLinkedQueue<HeartRateReading> heartRateReadings = new ConcurrentLinkedQueue<>();
    private final AtomicInteger currentHeartRate = new AtomicInteger(0);
    
    // Statistics tracking
    private int minHeartRate = Integer.MAX_VALUE;
    private int maxHeartRate = Integer.MIN_VALUE;
    private long totalReadings = 0;
    private long sumHeartRate = 0;
    
    public class HeartRateMonitorBinder extends Binder {
        HeartRateMonitorService getService() {
            return HeartRateMonitorService.this;
        }
    }
    
    public static class HeartRateReading {
        public final int heartRate;
        public final long timestamp;
        public final String source;
        
        public HeartRateReading(int heartRate, long timestamp, String source) {
            this.heartRate = heartRate;
            this.timestamp = timestamp;
            this.source = source;
        }
        
        @Override
        public String toString() {
            return "HeartRateReading{" +
                "heartRate=" + heartRate +
                ", timestamp=" + timestamp +
                ", source='" + source + '\'' +
                '}';
        }
    }
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "Heart Rate Monitor Service created");
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "Heart Rate Monitor Service started");
        return START_STICKY; // Restart if killed
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        Log.d(TAG, "Heart Rate Monitor Service bound");
        return binder;
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "Heart Rate Monitor Service destroyed");
    }
    
    /**
     * Add a new heart rate reading
     */
    public void addHeartRateReading(int heartRate) {
        addHeartRateReading(heartRate, "device");
    }
    
    /**
     * Add a new heart rate reading with source
     */
    public void addHeartRateReading(int heartRate, String source) {
        if (heartRate <= 0 || heartRate > 250) {
            Log.w(TAG, "Invalid heart rate reading: " + heartRate);
            return;
        }
        
        long timestamp = System.currentTimeMillis();
        HeartRateReading reading = new HeartRateReading(heartRate, timestamp, source);
        
        // Add to queue
        heartRateReadings.offer(reading);
        
        // Remove old readings if queue is too large
        while (heartRateReadings.size() > MAX_READINGS) {
            heartRateReadings.poll();
        }
        
        // Update current reading
        currentHeartRate.set(heartRate);
        
        // Update statistics
        updateStatistics(heartRate);
        
        Log.d(TAG, "Added heart rate reading: " + reading);
    }
    
    private void updateStatistics(int heartRate) {
        totalReadings++;
        sumHeartRate += heartRate;
        
        if (heartRate < minHeartRate) {
            minHeartRate = heartRate;
        }
        
        if (heartRate > maxHeartRate) {
            maxHeartRate = heartRate;
        }
    }
    
    /**
     * Get the current heart rate
     */
    public int getCurrentHeartRate() {
        return currentHeartRate.get();
    }
    
    /**
     * Get the latest heart rate reading
     */
    public HeartRateReading getLatestReading() {
        HeartRateReading[] readings = heartRateReadings.toArray(new HeartRateReading[0]);
        if (readings.length > 0) {
            return readings[readings.length - 1];
        }
        return null;
    }
    
    /**
     * Get all heart rate readings
     */
    public List<HeartRateReading> getAllReadings() {
        return new ArrayList<>(heartRateReadings);
    }
    
    /**
     * Get heart rate readings within a time range
     */
    public List<HeartRateReading> getReadingsInRange(long startTime, long endTime) {
        List<HeartRateReading> result = new ArrayList<>();
        
        for (HeartRateReading reading : heartRateReadings) {
            if (reading.timestamp >= startTime && reading.timestamp <= endTime) {
                result.add(reading);
            }
        }
        
        return result;
    }
    
    /**
     * Get recent heart rate readings (last N readings)
     */
    public List<HeartRateReading> getRecentReadings(int count) {
        List<HeartRateReading> allReadings = new ArrayList<>(heartRateReadings);
        int size = allReadings.size();
        
        if (size <= count) {
            return allReadings;
        }
        
        return allReadings.subList(size - count, size);
    }
    
    /**
     * Calculate average heart rate
     */
    public double getAverageHeartRate() {
        if (totalReadings == 0) {
            return 0.0;
        }
        return (double) sumHeartRate / totalReadings;
    }
    
    /**
     * Get minimum heart rate
     */
    public int getMinHeartRate() {
        return minHeartRate == Integer.MAX_VALUE ? 0 : minHeartRate;
    }
    
    /**
     * Get maximum heart rate
     */
    public int getMaxHeartRate() {
        return maxHeartRate == Integer.MIN_VALUE ? 0 : maxHeartRate;
    }
    
    /**
     * Get total number of readings
     */
    public long getTotalReadings() {
        return totalReadings;
    }
    
    /**
     * Calculate heart rate variability (RMSSD)
     */
    public double getHeartRateVariability() {
        List<HeartRateReading> readings = getAllReadings();
        
        if (readings.size() < 2) {
            return 0.0;
        }
        
        double sumSquaredDifferences = 0.0;
        int validDifferences = 0;
        
        for (int i = 1; i < readings.size(); i++) {
            HeartRateReading current = readings.get(i);
            HeartRateReading previous = readings.get(i - 1);
            
            // Only calculate if readings are close in time (within 10 seconds)
            if (current.timestamp - previous.timestamp <= 10000) {
                double difference = current.heartRate - previous.heartRate;
                sumSquaredDifferences += difference * difference;
                validDifferences++;
            }
        }
        
        if (validDifferences == 0) {
            return 0.0;
        }
        
        return Math.sqrt(sumSquaredDifferences / validDifferences);
    }
    
    /**
     * Get heart rate statistics
     */
    public HeartRateStatistics getStatistics() {
        return new HeartRateStatistics(
            getCurrentHeartRate(),
            getAverageHeartRate(),
            getMinHeartRate(),
            getMaxHeartRate(),
            getHeartRateVariability(),
            getTotalReadings(),
            heartRateReadings.size()
        );
    }
    
    /**
     * Clear all readings and reset statistics
     */
    public void clearReadings() {
        heartRateReadings.clear();
        currentHeartRate.set(0);
        minHeartRate = Integer.MAX_VALUE;
        maxHeartRate = Integer.MIN_VALUE;
        totalReadings = 0;
        sumHeartRate = 0;
        
        Log.d(TAG, "All heart rate readings cleared");
    }
    
    /**
     * Export readings as CSV format
     */
    public String exportToCsv() {
        StringBuilder csv = new StringBuilder();
        csv.append("timestamp,heart_rate,source\n");
        
        for (HeartRateReading reading : heartRateReadings) {
            csv.append(reading.timestamp)
               .append(",")
               .append(reading.heartRate)
               .append(",")
               .append(reading.source)
               .append("\n");
        }
        
        return csv.toString();
    }
    
    public static class HeartRateStatistics {
        public final int currentHeartRate;
        public final double averageHeartRate;
        public final int minHeartRate;
        public final int maxHeartRate;
        public final double heartRateVariability;
        public final long totalReadings;
        public final int currentReadings;
        
        public HeartRateStatistics(int currentHeartRate, double averageHeartRate, 
                                 int minHeartRate, int maxHeartRate, 
                                 double heartRateVariability, long totalReadings, 
                                 int currentReadings) {
            this.currentHeartRate = currentHeartRate;
            this.averageHeartRate = averageHeartRate;
            this.minHeartRate = minHeartRate;
            this.maxHeartRate = maxHeartRate;
            this.heartRateVariability = heartRateVariability;
            this.totalReadings = totalReadings;
            this.currentReadings = currentReadings;
        }
        
        @Override
        public String toString() {
            return "HeartRateStatistics{" +
                "currentHeartRate=" + currentHeartRate +
                ", averageHeartRate=" + String.format("%.1f", averageHeartRate) +
                ", minHeartRate=" + minHeartRate +
                ", maxHeartRate=" + maxHeartRate +
                ", heartRateVariability=" + String.format("%.2f", heartRateVariability) +
                ", totalReadings=" + totalReadings +
                ", currentReadings=" + currentReadings +
                '}';
        }
    }
}
