## Example: Full MainActivity with BLE + API

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var lstmProcessor: LSTMProcessor
    private lateinit var apiService: ApiService

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize LSTM and API
        lstmProcessor = LSTMProcessor(this)
        apiService = Retrofit.Builder()
            .baseUrl("http://10.0.2.2:5000/")  // Localhost for emulator
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)

        // Simulate real-time data
        simulateRealTimeData()

        // Set up BLE (optional)
        setupBLE()
    }

    private fun simulateRealTimeData() {
        val wellnessScores = List(20) { 0.7f + it * 0.01f }
        val hours = List(20) { it % 24.toFloat() }
        val hasEvents = List(20) { if (it % 5 == 0) 1f else 0f }
        val sleepDurations = List(20) { 7f + (it % 3) * 0.1f }

        val output = lstmProcessor.processWellnessData(
            wellnessScores, hours, hasEvents, sleepDurations
        )
        findViewById<TextView>(R.id.outputText).text =
            "Trend: ${output[0]}\nAlert: ${output[1]}"

        // Send to Flask
        sendDataToCloud(output, hours.last(), hasEvents.last(), sleepDurations.last())
    }

    private fun sendDataToCloud(
        output: FloatArray,
        hour: Float,
        hasEvent: Float,
        sleepDuration: Float
    ) {
        GlobalScope.launch(Dispatchers.IO) {
            try {
                apiService.sendData(mapOf(
                    "child_id" to "child_123",
                    "wellness_metrics" to mapOf(
                        "trend" to output[0],
                        "alert" to output[1]
                    ),
                    "context" to mapOf(
                        "hour" to hour,
                        "has_event" to hasEvent,
                        "sleep_duration" to sleepDuration
                    )
                ))
            } catch (e: Exception) {
                Log.e("API", "Error sending data", e)
            }
        }
    }

    private fun setupBLE() {
        // Implement BLE scanning/connection here
    }
}
```
```