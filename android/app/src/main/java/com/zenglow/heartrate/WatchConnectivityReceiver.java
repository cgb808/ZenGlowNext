package com.zenglow.heartrate;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.samsung.android.sdk.accessory.SAAgent;

public class WatchConnectivityReceiver extends BroadcastReceiver {
    private static final String TAG = "WatchConnectivity";
    
    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        Log.d(TAG, "Received broadcast: " + action);
        
        if ("com.samsung.accessory.action.SERVICE_CONNECTION_REQUESTED".equals(action)) {
            Log.d(TAG, "Galaxy Watch connection requested");
            
            // Start the Galaxy Watch service
            Intent serviceIntent = new Intent(context, GalaxyWatchService.class);
            context.startService(serviceIntent);
            
            // Notify the main activity if it's running
            Intent notifyIntent = new Intent("com.zenglow.heartrate.WATCH_CONNECTION_REQUESTED");
            context.sendBroadcast(notifyIntent);
        }
    }
}
