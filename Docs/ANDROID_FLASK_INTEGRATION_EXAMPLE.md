## Example: Full Integration with Flask Backend

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