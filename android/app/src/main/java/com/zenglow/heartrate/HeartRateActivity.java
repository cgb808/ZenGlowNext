package com.zenglow.heartrate;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.samsung.android.sdk.accessory.SA;
import com.samsung.android.sdk.accessory.SAAgent;
import com.samsung.android.sdk.accessory.SAPeerAgent;
import com.samsung.android.sdk.accessory.SASocket;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public class HeartRateActivity extends Activity implements SensorEventListener {
    private static final String TAG = "ZenGlow_HeartRate";
    private static final int PERMISSION_REQUEST_CODE = 100;
    
    // UI Components
    private TextView heartRateDisplay;
    private TextView statusDisplay;
    private TextView onBodyStatusDisplay;
    private Button toggleMonitoringButton;
    private Button exportDataButton;
    
    // Sensor Management
    private SensorManager sensorManager;
    private Sensor heartRateSensor;
    private boolean isMonitoring = false;
    private AtomicBoolean isOnBody = new AtomicBoolean(false);
    
    // Galaxy Watch Integration
    private SAAgent galaxyWatchAgent;
    private SASocket watchSocket;
    private BluetoothAdapter bluetoothAdapter;
    
    // Health Data Services
    private SamsungHealthService healthService;
    private HeartRateMonitorService monitorService;
    private GalaxyWatchService watchService;
    private HealthDataExportService exportService;
    
    // Data Management
    private Handler uiHandler;
    private int currentHeartRate = 0;
    private long lastHeartRateTime = 0;
    private static final int HEART_RATE_TIMEOUT = 10000; // 10 seconds
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_heart_rate);
        
        initializeUI();
        initializeServices();
        requestPermissions();
        initializeSensors();
        initializeGalaxyWatch();
        
        uiHandler = new Handler(Looper.getMainLooper());
        startHeartRateValidation();
    }
    
    private void initializeUI() {
        heartRateDisplay = findViewById(R.id.heart_rate_display);
        statusDisplay = findViewById(R.id.status_display);
        onBodyStatusDisplay = findViewById(R.id.on_body_status);
        toggleMonitoringButton = findViewById(R.id.toggle_monitoring_button);
        exportDataButton = findViewById(R.id.export_data_button);
        
        toggleMonitoringButton.setOnClickListener(v -> toggleHeartRateMonitoring());
        exportDataButton.setOnClickListener(v -> exportHealthData());
        
        updateUI();
    }
    
    private void initializeServices() {
        healthService = new SamsungHealthService(this);
        monitorService = new HeartRateMonitorService();
        watchService = new GalaxyWatchService(this);
        exportService = new HealthDataExportService(this);
    }
    
    private void requestPermissions() {
        String[] permissions = {
            Manifest.permission.BODY_SENSORS,
            Manifest.permission.BODY_SENSORS_BACKGROUND,
            Manifest.permission.ACCESS_HEART_RATE,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
        };
        
        boolean needsPermission = false;
        for (String permission : permissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                needsPermission = true;
                break;
            }
        }
        
        if (needsPermission) {
            ActivityCompat.requestPermissions(this, permissions, PERMISSION_REQUEST_CODE);
        }
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            
            if (allGranted) {
                Log.d(TAG, "All permissions granted");
                initializeSensors();
                initializeGalaxyWatch();
            } else {
                Toast.makeText(this, "Permissions required for heart rate monitoring", Toast.LENGTH_LONG).show();
            }
        }
    }
    
    private void initializeSensors() {
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            heartRateSensor = sensorManager.getDefaultSensor(Sensor.TYPE_HEART_RATE);
            
            if (heartRateSensor == null) {
                Log.w(TAG, "No heart rate sensor available on device");
                statusDisplay.setText("No heart rate sensor detected - Galaxy Watch required");
            } else {
                Log.d(TAG, "Heart rate sensor found: " + heartRateSensor.getName());
                statusDisplay.setText("Heart rate sensor ready");
            }
        }
    }
    
    private void initializeGalaxyWatch() {
        BluetoothManager bluetoothManager = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
        if (bluetoothManager != null) {
            bluetoothAdapter = bluetoothManager.getAdapter();
        }
        
        // Initialize Samsung Accessory SDK
        SA sa = new SA();
        try {
            sa.initialize(this);
            galaxyWatchAgent = new SAAgent(TAG) {
                @Override
                protected void onServiceConnectionRequested(SAPeerAgent peerAgent) {
                    Log.d(TAG, "Galaxy Watch connection requested");
                    acceptServiceConnectionRequest(peerAgent);
                }
                
                @Override
                protected void onServiceConnectionResponse(SAPeerAgent peerAgent, SASocket socket, int result) {
                    if (result == CONNECTION_SUCCESS) {
                        Log.d(TAG, "Galaxy Watch connected successfully");
                        watchSocket = socket;
                        statusDisplay.setText("Galaxy Watch connected");
                        watchService.setConnected(true);
                    } else {
                        Log.e(TAG, "Galaxy Watch connection failed: " + result);
                        statusDisplay.setText("Galaxy Watch connection failed");
                    }
                }
                
                @Override
                protected void onError(SAPeerAgent peerAgent, String errorMessage, int errorCode) {
                    Log.e(TAG, "Galaxy Watch error: " + errorMessage + " (Code: " + errorCode + ")");
                    statusDisplay.setText("Galaxy Watch error: " + errorMessage);
                }
            };
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize Samsung Accessory SDK", e);
            statusDisplay.setText("Galaxy Watch SDK initialization failed");
        }
    }
    
    private void toggleHeartRateMonitoring() {
        if (isMonitoring) {
            stopHeartRateMonitoring();
        } else {
            startHeartRateMonitoring();
        }
    }
    
    private void startHeartRateMonitoring() {
        if (heartRateSensor != null && sensorManager != null) {
            boolean registered = sensorManager.registerListener(this, heartRateSensor, SensorManager.SENSOR_DELAY_NORMAL);
            if (registered) {
                isMonitoring = true;
                toggleMonitoringButton.setText("Stop Monitoring");
                statusDisplay.setText("Monitoring heart rate...");
                Log.d(TAG, "Heart rate monitoring started");
                
                // Start Samsung Health service
                healthService.startMonitoring();
                
                // Start Galaxy Watch monitoring
                watchService.startHeartRateMonitoring();
            } else {
                Log.e(TAG, "Failed to register heart rate sensor listener");
                statusDisplay.setText("Failed to start monitoring");
            }
        } else {
            Log.w(TAG, "Heart rate sensor not available");
            statusDisplay.setText("Heart rate sensor not available - trying Galaxy Watch...");
            
            // Try Galaxy Watch only
            watchService.startHeartRateMonitoring();
            isMonitoring = true;
            toggleMonitoringButton.setText("Stop Monitoring");
        }
    }
    
    private void stopHeartRateMonitoring() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        
        isMonitoring = false;
        toggleMonitoringButton.setText("Start Monitoring");
        statusDisplay.setText("Monitoring stopped");
        heartRateDisplay.setText("--");
        
        // Stop services
        healthService.stopMonitoring();
        watchService.stopHeartRateMonitoring();
        
        Log.d(TAG, "Heart rate monitoring stopped");
    }
    
    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_HEART_RATE) {
            float heartRateValue = event.values[0];
            currentHeartRate = Math.round(heartRateValue);
            lastHeartRateTime = System.currentTimeMillis();
            
            // Check if sensor is on body (heart rate > 0 indicates on-body)
            isOnBody.set(currentHeartRate > 0);
            
            Log.d(TAG, "Heart rate: " + currentHeartRate + " BPM, On-body: " + isOnBody.get());
            
            runOnUiThread(() -> {
                if (currentHeartRate > 0) {
                    heartRateDisplay.setText(currentHeartRate + " BPM");
                    onBodyStatusDisplay.setText("Sensor: ON BODY");
                    
                    // Store data
                    healthService.recordHeartRate(currentHeartRate, System.currentTimeMillis());
                    monitorService.addHeartRateReading(currentHeartRate);
                } else {
                    heartRateDisplay.setText("--");
                    onBodyStatusDisplay.setText("Sensor: OFF BODY");
                }
                
                statusDisplay.setText("Last reading: " + 
                    new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date()));
            });
        }
    }
    
    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        Log.d(TAG, "Heart rate sensor accuracy changed: " + accuracy);
    }
    
    private void startHeartRateValidation() {
        uiHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (isMonitoring) {
                    long timeSinceLastReading = System.currentTimeMillis() - lastHeartRateTime;
                    
                    if (timeSinceLastReading > HEART_RATE_TIMEOUT) {
                        runOnUiThread(() -> {
                            heartRateDisplay.setText("--");
                            if (heartRateSensor != null) {
                                onBodyStatusDisplay.setText("Sensor: CHECK PLACEMENT");
                            } else {
                                onBodyStatusDisplay.setText("Galaxy Watch: CHECK CONNECTION");
                            }
                        });
                    }
                    
                    // Check Galaxy Watch heart rate
                    int watchHeartRate = watchService.getLatestHeartRate();
                    if (watchHeartRate > 0) {
                        runOnUiThread(() -> {
                            heartRateDisplay.setText(watchHeartRate + " BPM");
                            onBodyStatusDisplay.setText("Galaxy Watch: ON BODY");
                            statusDisplay.setText("Galaxy Watch - Last reading: " + 
                                new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date()));
                        });
                        
                        // Store Galaxy Watch data
                        healthService.recordHeartRate(watchHeartRate, System.currentTimeMillis());
                        monitorService.addHeartRateReading(watchHeartRate);
                    }
                }
                
                // Schedule next validation
                uiHandler.postDelayed(this, 2000); // Check every 2 seconds
            }
        }, 2000);
    }
    
    private void exportHealthData() {
        statusDisplay.setText("Exporting health data...");
        
        // Export to all supported platforms
        exportService.exportToSamsungHealth();
        exportService.exportToAppleHealth();
        exportService.exportToGoogleFit();
        exportService.exportToGarmin();
        
        Toast.makeText(this, "Health data export initiated", Toast.LENGTH_SHORT).show();
        statusDisplay.setText("Export completed");
    }
    
    private void updateUI() {
        if (!isMonitoring) {
            heartRateDisplay.setText("--");
            onBodyStatusDisplay.setText("Not monitoring");
            statusDisplay.setText("Ready to monitor");
            toggleMonitoringButton.setText("Start Monitoring");
        }
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        if (isMonitoring && heartRateSensor != null && sensorManager != null) {
            sensorManager.registerListener(this, heartRateSensor, SensorManager.SENSOR_DELAY_NORMAL);
        }
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isMonitoring) {
            stopHeartRateMonitoring();
        }
        
        // Cleanup services
        if (healthService != null) {
            healthService.cleanup();
        }
        if (watchService != null) {
            watchService.cleanup();
        }
        if (exportService != null) {
            exportService.cleanup();
        }
        
        // Cleanup Galaxy Watch connection
        if (watchSocket != null) {
            watchSocket.close();
        }
        if (galaxyWatchAgent != null) {
            galaxyWatchAgent.releaseAgent();
        }
    }
}
