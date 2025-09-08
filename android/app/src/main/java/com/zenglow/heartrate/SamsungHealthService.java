package com.zenglow.heartrate;

import android.content.Context;
import android.util.Log;

import com.samsung.android.sdk.healthdata.HealthConnectionErrorResult;
import com.samsung.android.sdk.healthdata.HealthConstants;
import com.samsung.android.sdk.healthdata.HealthData;
import com.samsung.android.sdk.healthdata.HealthDataResolver;
import com.samsung.android.sdk.healthdata.HealthDataService;
import com.samsung.android.sdk.healthdata.HealthDataStore;
import com.samsung.android.sdk.healthdata.HealthPermissionManager;
import com.samsung.android.sdk.healthdata.HealthResultHolder;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

public class SamsungHealthService {
    private static final String TAG = "SamsungHealth";
    
    private Context context;
    private HealthDataStore healthDataStore;
    private HealthDataService healthDataService;
    private boolean isConnected = false;
    private boolean isMonitoring = false;
    
    // Permission sets
    private final Set<HealthPermissionManager.PermissionKey> permissionKeySet;
    
    public SamsungHealthService(Context context) {
        this.context = context;
        this.permissionKeySet = new HashSet<>();
        initializePermissions();
        connectToSamsungHealth();
    }
    
    private void initializePermissions() {
        // Heart rate permissions
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.HeartRate.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.READ));
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.HeartRate.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.WRITE));
            
        // Exercise permissions for context
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.Exercise.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.READ));
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.Exercise.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.WRITE));
            
        // Sleep permissions for wellness context
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.Sleep.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.READ));
        permissionKeySet.add(new HealthPermissionManager.PermissionKey(
            HealthConstants.Sleep.HEALTH_DATA_TYPE, HealthPermissionManager.PermissionType.WRITE));
    }
    
    private void connectToSamsungHealth() {
        healthDataService = new HealthDataService();
        
        try {
            healthDataService.initialize(context);
            Log.d(TAG, "Samsung Health service initialized");
            
            // Create health data store
            healthDataStore = new HealthDataStore(context, mConnectionListener);
            healthDataStore.connectService();
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize Samsung Health service", e);
        }
    }
    
    private final HealthDataStore.ConnectionListener mConnectionListener = new HealthDataStore.ConnectionListener() {
        @Override
        public void onConnected() {
            Log.d(TAG, "Samsung Health connected");
            isConnected = true;
            requestPermissions();
        }
        
        @Override
        public void onConnectionFailed(HealthConnectionErrorResult error) {
            Log.e(TAG, "Samsung Health connection failed: " + error.getErrorCode() + " - " + error.getErrorMessage());
            isConnected = false;
            
            // Retry connection after delay
            new android.os.Handler().postDelayed(() -> {
                if (!isConnected) {
                    Log.d(TAG, "Retrying Samsung Health connection...");
                    healthDataStore.connectService();
                }
            }, 5000);
        }
        
        @Override
        public void onDisconnected() {
            Log.d(TAG, "Samsung Health disconnected");
            isConnected = false;
        }
    };
    
    private void requestPermissions() {
        HealthPermissionManager permissionManager = new HealthPermissionManager(healthDataStore);
        
        try {
            // Check if permissions are already granted
            Map<HealthPermissionManager.PermissionKey, Boolean> resultMap = 
                permissionManager.isPermissionAcquired(permissionKeySet);
                
            boolean allPermissionsGranted = true;
            for (Boolean granted : resultMap.values()) {
                if (!granted) {
                    allPermissionsGranted = false;
                    break;
                }
            }
            
            if (!allPermissionsGranted) {
                // Request permissions
                permissionManager.requestPermissions(permissionKeySet, context)
                    .setResultListener(result -> {
                        Map<HealthPermissionManager.PermissionKey, Boolean> grantedPermissions = result.getResultMap();
                        
                        boolean allGranted = true;
                        for (Map.Entry<HealthPermissionManager.PermissionKey, Boolean> entry : grantedPermissions.entrySet()) {
                            if (!entry.getValue()) {
                                Log.w(TAG, "Permission denied: " + entry.getKey().getDataType());
                                allGranted = false;
                            }
                        }
                        
                        if (allGranted) {
                            Log.d(TAG, "All Samsung Health permissions granted");
                        } else {
                            Log.w(TAG, "Some Samsung Health permissions were denied");
                        }
                    });
            } else {
                Log.d(TAG, "All Samsung Health permissions already granted");
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Error requesting Samsung Health permissions", e);
        }
    }
    
    public void startMonitoring() {
        if (!isConnected) {
            Log.w(TAG, "Samsung Health not connected");
            return;
        }
        
        isMonitoring = true;
        Log.d(TAG, "Samsung Health monitoring started");
    }
    
    public void stopMonitoring() {
        isMonitoring = false;
        Log.d(TAG, "Samsung Health monitoring stopped");
    }
    
    public void recordHeartRate(int heartRate, long timestamp) {
        if (!isConnected || !isMonitoring) {
            Log.w(TAG, "Cannot record heart rate - not connected or not monitoring");
            return;
        }
        
        try {
            // Create heart rate data
            HealthData heartRateData = new HealthData();
            heartRateData.setSourcePackageName(context.getPackageName());
            heartRateData.put(HealthConstants.HeartRate.HEART_RATE, heartRate);
            heartRateData.put(HealthConstants.HeartRate.START_TIME, timestamp);
            heartRateData.put(HealthConstants.HeartRate.END_TIME, timestamp);
            heartRateData.put(HealthConstants.HeartRate.TIME_OFFSET, TimeUnit.MILLISECONDS.convert(
                java.util.TimeZone.getDefault().getOffset(timestamp), TimeUnit.MILLISECONDS));
            
            // Insert data
            HealthDataResolver resolver = new HealthDataResolver(healthDataStore, null);
            resolver.insert(heartRateData)
                .setResultListener(result -> {
                    if (result.getStatus() == HealthResultHolder.BaseResult.STATUS_SUCCESSFUL) {
                        Log.d(TAG, "Heart rate recorded successfully: " + heartRate + " BPM");
                    } else {
                        Log.e(TAG, "Failed to record heart rate: " + result.getStatus());
                    }
                });
                
        } catch (Exception e) {
            Log.e(TAG, "Error recording heart rate to Samsung Health", e);
        }
    }
    
    public void recordExerciseSession(String exerciseType, long startTime, long endTime, int avgHeartRate, int maxHeartRate) {
        if (!isConnected) {
            Log.w(TAG, "Cannot record exercise - Samsung Health not connected");
            return;
        }
        
        try {
            // Create exercise data
            HealthData exerciseData = new HealthData();
            exerciseData.setSourcePackageName(context.getPackageName());
            exerciseData.put(HealthConstants.Exercise.EXERCISE_TYPE, getExerciseTypeId(exerciseType));
            exerciseData.put(HealthConstants.Exercise.START_TIME, startTime);
            exerciseData.put(HealthConstants.Exercise.END_TIME, endTime);
            exerciseData.put(HealthConstants.Exercise.DURATION, endTime - startTime);
            
            if (avgHeartRate > 0) {
                exerciseData.put(HealthConstants.Exercise.MEAN_HEART_RATE, avgHeartRate);
            }
            if (maxHeartRate > 0) {
                exerciseData.put(HealthConstants.Exercise.MAX_HEART_RATE, maxHeartRate);
            }
            
            exerciseData.put(HealthConstants.Exercise.TIME_OFFSET, TimeUnit.MILLISECONDS.convert(
                java.util.TimeZone.getDefault().getOffset(startTime), TimeUnit.MILLISECONDS));
            
            // Insert exercise data
            HealthDataResolver resolver = new HealthDataResolver(healthDataStore, null);
            resolver.insert(exerciseData)
                .setResultListener(result -> {
                    if (result.getStatus() == HealthResultHolder.BaseResult.STATUS_SUCCESSFUL) {
                        Log.d(TAG, "Exercise session recorded: " + exerciseType);
                    } else {
                        Log.e(TAG, "Failed to record exercise session: " + result.getStatus());
                    }
                });
                
        } catch (Exception e) {
            Log.e(TAG, "Error recording exercise session", e);
        }
    }
    
    private int getExerciseTypeId(String exerciseType) {
        // Map common exercise types to Samsung Health constants
        switch (exerciseType.toLowerCase()) {
            case "meditation":
            case "mindfulness":
                return HealthConstants.Exercise.EXERCISE_TYPE_MEDITATION;
            case "yoga":
                return HealthConstants.Exercise.EXERCISE_TYPE_YOGA;
            case "breathing":
                return HealthConstants.Exercise.EXERCISE_TYPE_BREATHING_EXERCISES;
            case "walking":
                return HealthConstants.Exercise.EXERCISE_TYPE_WALKING;
            case "running":
                return HealthConstants.Exercise.EXERCISE_TYPE_RUNNING;
            case "cycling":
                return HealthConstants.Exercise.EXERCISE_TYPE_CYCLING;
            default:
                return HealthConstants.Exercise.EXERCISE_TYPE_OTHERS;
        }
    }
    
    public boolean isConnected() {
        return isConnected;
    }
    
    public boolean isMonitoring() {
        return isMonitoring;
    }
    
    public void cleanup() {
        if (healthDataStore != null && isConnected) {
            healthDataStore.disconnectService();
        }
        isConnected = false;
        isMonitoring = false;
        Log.d(TAG, "Samsung Health service cleaned up");
    }
}
