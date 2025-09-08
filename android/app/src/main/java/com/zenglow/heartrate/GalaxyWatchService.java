package com.zenglow.heartrate;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.samsung.android.sdk.accessory.SA;
import com.samsung.android.sdk.accessory.SAAgent;
import com.samsung.android.sdk.accessory.SAPeerAgent;
import com.samsung.android.sdk.accessory.SASocket;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public class GalaxyWatchService {
    private static final String TAG = "GalaxyWatch";
    private static final String CHANNEL_ID = "ZenGlow_HeartRate_Channel";
    
    private Context context;
    private SAAgent watchAgent;
    private SASocket watchSocket;
    private AtomicBoolean isConnected = new AtomicBoolean(false);
    private AtomicBoolean isMonitoring = new AtomicBoolean(false);
    private AtomicInteger latestHeartRate = new AtomicInteger(0);
    private Handler uiHandler;
    
    // Heart rate monitoring
    private long lastHeartRateTime = 0;
    private HeartRateCallback heartRateCallback;
    
    public interface HeartRateCallback {
        void onHeartRateReceived(int heartRate, long timestamp);
        void onConnectionStatusChanged(boolean connected);
        void onError(String error);
    }
    
    public GalaxyWatchService(Context context) {
        this.context = context;
        this.uiHandler = new Handler(Looper.getMainLooper());
        initializeWatchAgent();
    }
    
    public void setHeartRateCallback(HeartRateCallback callback) {
        this.heartRateCallback = callback;
    }
    
    private void initializeWatchAgent() {
        SA sa = new SA();
        try {
            sa.initialize(context);
            
            watchAgent = new SAAgent(TAG) {
                @Override
                protected void onServiceConnectionRequested(SAPeerAgent peerAgent) {
                    Log.d(TAG, "Galaxy Watch connection requested from: " + peerAgent.getPeerName());
                    acceptServiceConnectionRequest(peerAgent);
                }
                
                @Override
                protected void onServiceConnectionResponse(SAPeerAgent peerAgent, SASocket socket, int result) {
                    if (result == CONNECTION_SUCCESS) {
                        Log.d(TAG, "Successfully connected to Galaxy Watch: " + peerAgent.getPeerName());
                        watchSocket = socket;
                        isConnected.set(true);
                        
                        setupSocketListener();
                        
                        // Notify callback
                        if (heartRateCallback != null) {
                            uiHandler.post(() -> heartRateCallback.onConnectionStatusChanged(true));
                        }
                        
                        // Send initial configuration
                        sendWatchConfiguration();
                        
                    } else {
                        Log.e(TAG, "Failed to connect to Galaxy Watch. Result: " + result);
                        isConnected.set(false);
                        
                        if (heartRateCallback != null) {
                            uiHandler.post(() -> heartRateCallback.onError("Connection failed: " + result));
                        }
                    }
                }
                
                @Override
                protected void onError(SAPeerAgent peerAgent, String errorMessage, int errorCode) {
                    Log.e(TAG, "Galaxy Watch error: " + errorMessage + " (Code: " + errorCode + ")");
                    isConnected.set(false);
                    
                    if (heartRateCallback != null) {
                        uiHandler.post(() -> heartRateCallback.onError("Watch error: " + errorMessage));
                    }
                }
                
                @Override
                protected void onPeerAgentUpdated(SAPeerAgent peerAgent, int result) {
                    Log.d(TAG, "Galaxy Watch peer agent updated: " + result);
                }
            };
            
            Log.d(TAG, "Galaxy Watch agent initialized");
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize Galaxy Watch agent", e);
            if (heartRateCallback != null) {
                uiHandler.post(() -> heartRateCallback.onError("Initialization failed: " + e.getMessage()));
            }
        }
    }
    
    private void setupSocketListener() {
        if (watchSocket == null) return;
        
        watchSocket.setSocketStatusListener(new SASocket.SocketStatusListener() {
            @Override
            public void onServiceConnectionLost(int reason) {
                Log.w(TAG, "Galaxy Watch connection lost. Reason: " + reason);
                isConnected.set(false);
                isMonitoring.set(false);
                
                if (heartRateCallback != null) {
                    uiHandler.post(() -> heartRateCallback.onConnectionStatusChanged(false));
                }
            }
            
            @Override
            public void onPeerSocketClosed(SAPeerAgent peerAgent, int reason) {
                Log.w(TAG, "Galaxy Watch socket closed. Reason: " + reason);
                isConnected.set(false);
                isMonitoring.set(false);
            }
        });
        
        // Set up data receive listener
        watchSocket.setReceiveDataListener(new SASocket.ReceiveDataListener() {
            @Override
            public void onReceive(int channelId, byte[] data) {
                try {
                    String receivedData = new String(data);
                    Log.d(TAG, "Received data from Galaxy Watch: " + receivedData);
                    
                    processWatchData(receivedData);
                    
                } catch (Exception e) {
                    Log.e(TAG, "Error processing watch data", e);
                }
            }
            
            @Override
            public void onError(int channelId, String errorMessage, int errorCode) {
                Log.e(TAG, "Data receive error: " + errorMessage + " (Code: " + errorCode + ")");
                if (heartRateCallback != null) {
                    uiHandler.post(() -> heartRateCallback.onError("Data error: " + errorMessage));
                }
            }
        });
    }
    
    private void processWatchData(String data) {
        try {
            JSONObject json = new JSONObject(data);
            String type = json.optString("type", "");
            
            switch (type) {
                case "heart_rate":
                    int heartRate = json.getInt("value");
                    long timestamp = json.optLong("timestamp", System.currentTimeMillis());
                    boolean onBody = json.optBoolean("on_body", true);
                    
                    if (heartRate > 0 && onBody) {
                        latestHeartRate.set(heartRate);
                        lastHeartRateTime = timestamp;
                        
                        Log.d(TAG, "Heart rate from Galaxy Watch: " + heartRate + " BPM");
                        
                        if (heartRateCallback != null) {
                            uiHandler.post(() -> heartRateCallback.onHeartRateReceived(heartRate, timestamp));
                        }
                    } else {
                        Log.d(TAG, "Galaxy Watch off-body or invalid reading: " + heartRate);
                    }
                    break;
                    
                case "sensor_status":
                    boolean sensorActive = json.getBoolean("active");
                    boolean onBodyStatus = json.optBoolean("on_body", false);
                    
                    Log.d(TAG, "Galaxy Watch sensor status - Active: " + sensorActive + ", On-body: " + onBodyStatus);
                    
                    if (!onBodyStatus) {
                        latestHeartRate.set(0);
                    }
                    break;
                    
                case "battery_status":
                    int batteryLevel = json.getInt("level");
                    Log.d(TAG, "Galaxy Watch battery level: " + batteryLevel + "%");
                    break;
                    
                default:
                    Log.d(TAG, "Unknown data type from Galaxy Watch: " + type);
                    break;
            }
            
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing watch data JSON", e);
        }
    }
    
    private void sendWatchConfiguration() {
        if (!isConnected.get() || watchSocket == null) return;
        
        try {
            JSONObject config = new JSONObject();
            config.put("type", "config");
            config.put("heart_rate_interval", 2000); // 2 seconds
            config.put("enable_continuous_monitoring", true);
            config.put("enable_on_body_detection", true);
            
            String configData = config.toString();
            
            watchSocket.send(CHANNEL_ID.hashCode(), configData.getBytes());
            Log.d(TAG, "Sent configuration to Galaxy Watch");
            
        } catch (JSONException | IOException e) {
            Log.e(TAG, "Error sending configuration to Galaxy Watch", e);
        }
    }
    
    public void startHeartRateMonitoring() {
        if (!isConnected.get()) {
            Log.w(TAG, "Cannot start monitoring - Galaxy Watch not connected");
            return;
        }
        
        if (isMonitoring.get()) {
            Log.d(TAG, "Heart rate monitoring already active");
            return;
        }
        
        try {
            JSONObject command = new JSONObject();
            command.put("type", "start_heart_rate");
            command.put("continuous", true);
            command.put("interval", 2000);
            
            String commandData = command.toString();
            
            if (watchSocket != null) {
                watchSocket.send(CHANNEL_ID.hashCode(), commandData.getBytes());
                isMonitoring.set(true);
                Log.d(TAG, "Started Galaxy Watch heart rate monitoring");
            }
            
        } catch (JSONException | IOException e) {
            Log.e(TAG, "Error starting Galaxy Watch heart rate monitoring", e);
        }
    }
    
    public void stopHeartRateMonitoring() {
        if (!isMonitoring.get()) {
            Log.d(TAG, "Heart rate monitoring not active");
            return;
        }
        
        try {
            JSONObject command = new JSONObject();
            command.put("type", "stop_heart_rate");
            
            String commandData = command.toString();
            
            if (watchSocket != null && isConnected.get()) {
                watchSocket.send(CHANNEL_ID.hashCode(), commandData.getBytes());
            }
            
            isMonitoring.set(false);
            latestHeartRate.set(0);
            Log.d(TAG, "Stopped Galaxy Watch heart rate monitoring");
            
        } catch (JSONException | IOException e) {
            Log.e(TAG, "Error stopping Galaxy Watch heart rate monitoring", e);
        }
    }
    
    public int getLatestHeartRate() {
        // Return 0 if data is too old (more than 10 seconds)
        if (System.currentTimeMillis() - lastHeartRateTime > 10000) {
            return 0;
        }
        return latestHeartRate.get();
    }
    
    public boolean isConnected() {
        return isConnected.get();
    }
    
    public boolean isMonitoring() {
        return isMonitoring.get();
    }
    
    public void setConnected(boolean connected) {
        isConnected.set(connected);
    }
    
    public long getLastHeartRateTime() {
        return lastHeartRateTime;
    }
    
    public void cleanup() {
        if (isMonitoring.get()) {
            stopHeartRateMonitoring();
        }
        
        if (watchSocket != null) {
            try {
                watchSocket.close();
            } catch (Exception e) {
                Log.e(TAG, "Error closing watch socket", e);
            }
            watchSocket = null;
        }
        
        if (watchAgent != null) {
            try {
                watchAgent.releaseAgent();
            } catch (Exception e) {
                Log.e(TAG, "Error releasing watch agent", e);
            }
            watchAgent = null;
        }
        
        isConnected.set(false);
        isMonitoring.set(false);
        latestHeartRate.set(0);
        
        Log.d(TAG, "Galaxy Watch service cleaned up");
    }
}
