## 1. Tools to Install

| Tool                                  | Purpose                           | Installation                                                                     |
| ------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------- |
| Android Studio                        | Android emulator + IDE            | [Download](https://developer.android.com/studio)                                 |
| Python 3.8+                           | Train TinyLSTM                    | [Download](https://www.python.org/downloads/)                                    |
| TensorFlow 2.x                        | Train/convert models              | `pip install tensorflow`                                                         |
| TensorFlow Lite (via full TensorFlow) | Run / convert models incl. mobile | Included in `tensorflow` (use `from tensorflow import lite`)                     |
| Java JDK 11+                          | Android development               | [Download](https://www.oracle.com/java/technologies/javase-jdk11-downloads.html) |

## 2. Train and Convert TinyLSTM for Mobile

> **🚀 Ready-to-Use Scripts Available!**  
> For production use, we provide standalone training and verification scripts:
> - **Training Script**: [`ai-workspace/models/tinylstm/train_tinylstm.py`](../ai-workspace/models/tinylstm/train_tinylstm.py)
> - **Verification Script**: [`ai-workspace/models/tinylstm/verify_tflite.py`](../ai-workspace/models/tinylstm/verify_tflite.py)  
> - **Documentation**: [`ai-workspace/models/tinylstm/README.md`](../ai-workspace/models/tinylstm/README.md)
>
> **Quick Start:**
> ```bash
> cd ai-workspace/models/tinylstm
> python train_tinylstm.py
> python verify_tflite.py mobile_lstm.tflite
> ```

### A. Train the Model

Use this script to train a TinyLSTM for mobile (16-32 units):

```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

# Simulate training data: [timesteps, features] → [trend, alert]
X_train = tf.random.normal((1000, 20, 4))  # 1000 samples, 20 timesteps, 4 features
y_train = tf.random.uniform((1000, 2), minval=0, maxval=1)  # [trend, alert]

model = Sequential([
    Input(shape=(20, 4)),
    LSTM(16, return_sequences=False),  # 16 units for mobile
    Dense(2, activation='sigmoid')    # [trend, alert]
])

model.compile(optimizer='adam', loss='mse')
model.fit(X_train, y_train, epochs=20)

# Save as TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]  # Quantization
tflite_model = converter.convert()

with open('mobile_lstm.tflite', 'wb') as f:
    f.write(tflite_model)
```

### B. Verify the Model

```python
# Load and test the TFLite model
interpreter = tf.lite.Interpreter(model_content=tflite_model)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Test inference
input_data = tf.random.normal((1, 20, 4))  # Batch of 1
interpreter.set_tensor(input_details[0]['index'], input_data.numpy())
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])
print("Output:", output)
```

## 2. Set Up Android Studio

### A. Create a New Project

Open Android Studio → New Project → Empty Activity.
Name: WellnessCompanion.
Language: Kotlin (recommended) or Java.
Minimum SDK: API 21 (Android 5.0).

### B. Add TensorFlow Lite Dependency

Edit `app/build.gradle` (Module-level):

```gradle
dependencies {
    implementation 'org.tensorflow:tensorflow-lite:2.8.0'
    implementation 'org.tensorflow:tensorflow-lite-support:0.4.0'
}
```

Sync Gradle.

### C. Add the .tflite Model

Copy `mobile_lstm.tflite` to `app/src/main/assets/`.
Right-click app → New → Folder → Assets Folder.

## 3. Load and Run TinyLSTM in Android

### A. Create a LSTMProcessor Class

```kotlin
// LSTMProcessor.kt
import android.content.Context
import org.tensorflow.lite.Interpreter
import java.nio.ByteBuffer
import java.nio.ByteOrder

class LSTMProcessor(context: Context) {
    private val interpreter: Interpreter

    init {
        // Load the TFLite model
        val modelFile = loadModelFile(context, "mobile_lstm.tflite")
        interpreter = Interpreter(modelFile)
    }

    fun predict(input: FloatArray): FloatArray {
        // Allocate input buffer (20 timesteps * 4 features)
        val inputBuffer = ByteBuffer.allocateDirect(20 * 4 * 4).apply {
            order(ByteOrder.nativeOrder())
            input.forEach { putFloat(it) }
            rewind()
        }

        // Allocate output buffer (2 values: trend + alert)
        val outputBuffer = FloatArray(2)
        interpreter.run(inputBuffer, outputBuffer)
        return outputBuffer
    }

    private fun loadModelFile(context: Context, filename: String): ByteBuffer {
        val fileDescriptor = context.assets.openFd(filename)
        val inputStream = fileDescriptor.createInputStream()
        val fileChannel = inputStream.channel
        val startOffset = fileDescriptor.startOffset
        val declaredLength = fileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }
}
```

### B. Use the Model in MainActivity

```kotlin
// MainActivity.kt
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var lstmProcessor: LSTMProcessor

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize LSTM processor
        lstmProcessor = LSTMProcessor(this)

        // Simulate input data: 20 timesteps * 4 features (wellness, hour, event, sleep)
        val input = FloatArray(20 * 4) { i ->
            when (i % 4) {
                0 -> 0.7f + (i / 4) * 0.01f  // Wellness trend
                1 -> (i / 4).toFloat()      // Hour of day
                2 -> if (i % 8 == 0) 1f else 0f  // School event
                else -> 7f + (i % 3) * 0.1f  // Sleep duration
            }
        }

        // Run inference
        val output = lstmProcessor.predict(input)
        findViewById<TextView>(R.id.outputText).text =
            "Trend: ${output[0]}\nAlert: ${output[1]}"
    }
}
```

### C. Update activity_main.xml

```xml
<!-- activity_main.xml -->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:id="@+id/outputText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Output will appear here"/>

</LinearLayout>
```

## 4. Test on Android Emulator

### A. Set Up an Emulator

In Android Studio, go to Tools → Device Manager → Create Virtual Device.
Select a device (e.g., Pixel 5) and system image (e.g., Android 11).
Click Finish and run the emulator.

### B. Run the App

Click Run (▶️) in Android Studio.
Select the emulator and wait for the app to launch.
Verify the output in the app (e.g., Trend: 0.75, Alert: 0.1).

### C. Debugging

- **Logcat:** View logs in Android Studio (View → Tool Windows → Logcat).
- **Common Issues:**
  - Model not found: Ensure `mobile_lstm.tflite` is in `app/src/main/assets/`.
  - Shape mismatch: Verify input shape matches the model (20 timesteps \* 4 features).
  - Permission issues: Grant storage permissions if loading external files.

## 5. Integrate with Wellness Pipeline

### A. Modify LSTMProcessor for Real Data

```kotlin
fun processWellnessData(
    wellnessScores: List<Float>,
    hours: List<Float>,
    hasEvents: List<Float>,
    sleepDurations: List<Float>
): FloatArray {
    require(wellnessScores.size == 20) { "Expected 20 timesteps" }
    val input = FloatArray(20 * 4)
    for (i in 0 until 20) {
        input[i * 4] = wellnessScores[i]     // Wellness score
        input[i * 4 + 1] = hours[i]           // Hour of day
        input[i * 4 + 2] = hasEvents[i]       // School event (1/0)
        input[i * 4 + 3] = sleepDurations[i]  // Sleep duration
    }
    return predict(input)
}
```

### B. Simulate Real-Time Data

```kotlin
// Simulate real-time data from wearable
fun simulateRealTimeData() {
    val wellnessScores = List(20) { 0.7f + it * 0.01f }  // Increasing trend
    val hours = List(20) { it % 24.toFloat() }          // Hour of day
    val hasEvents = List(20) { if (it % 5 == 0) 1f else 0f }  // Events every 5 timesteps
    val sleepDurations = List(20) { 7f + (it % 3) * 0.1f }   // Sleep data

    val output = processWellnessData(wellnessScores, hours, hasEvents, sleepDurations)
    findViewById<TextView>(R.id.outputText).text =
        "Trend: ${output[0]}\nAlert: ${output[1]}"
}
```

### C. Connect to BLE (Optional)

To receive real data from a wearable:

- Add BLE permissions to `AndroidManifest.xml`:

  ```xml
  <uses-permission android:name="android.permission.BLUETOOTH"/>
  <uses-permission android:name="android.permission.BLUETOOTH_ADMIN"/>
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
  ```

- Use the Android BLE API to scan for wearables and parse JSON payloads.

## 6. Launch on a Physical Device

### A. Build an APK

In Android Studio, go to Build → Build Bundle(s)/APK(s) → Build APK.
Wait for the build to complete (output in `app/build/outputs/apk/debug/`).

### B. Transfer to Device

Connect your Android phone via USB.
Run:
`adb install app/build/outputs/apk/debug/app-debug.apk`

Open the app and test with real data.

## 7. Performance Optimization

| Issue                | Solution                                                                        |
| -------------------- | ------------------------------------------------------------------------------- |
| Slow inference       | Use FP16 quantization (`converter.optimizations = [tf.lite.Optimize.DEFAULT]`). |
| High memory usage    | Reduce LSTM units to 16 or use 8-bit quantization.                              |
| BLE connection drops | Implement retry logic and reduce payload size.                                  |
| Model too large      | Train with fewer units (e.g., 8-16) or timesteps (e.g., 10).                    |

## 8. Example: Full Integration with Flask Backend

### A. Send Data to Cloud

```kotlin
// Use Retrofit to send processed data to Flask
interface ApiService {
    @POST("/api/ingest")
    suspend fun sendData(@Body data: Map<String, Any>): Response<Void>
}

val retrofit = Retrofit.Builder()
    .baseUrl("http://your-flask-server:5000/")
    .addConverterFactory(GsonConverterFactory.create())
    .build()

val apiService = retrofit.create(ApiService::class.java)

// Send data to Flask
GlobalScope.launch(Dispatchers.IO) {
    try {
        val response = apiService.sendData(mapOf(
            "child_id" to "child_123",
            "wellness_metrics" to mapOf(
                "trend" to output[0],
                "alert" to output[1]
            ),
            "context" to mapOf(
                "hour" to hours.last(),
                "has_event" to hasEvents.last(),
                "sleep_duration" to sleepDurations.last()
            )
        ))
        if (response.isSuccessful) {
            Log.d("API", "Data sent successfully")
        }
    } catch (e: Exception) {
        Log.e("API", "Error sending data", e)
    }
}
```

### B. Receive Recommendations

```kotlin
// Poll Flask for recommendations
fun fetchRecommendations() {
    GlobalScope.launch(Dispatchers.IO) {
        try {
            val response = apiService.getRecommendations("child_123")
            if (response.isSuccessful) {
                val recommendation = response.body()?.string()
                runOnUiThread {
                    findViewById<TextView>(R.id.recommendationText).text = recommendation
                }
            }
        } catch (e: Exception) {
            Log.e("API", "Error fetching recommendations", e)
        }
    }
}
```
