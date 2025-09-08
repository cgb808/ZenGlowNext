## On-Device Models Summary

There will be three TinyLSTM models, each with a specific role:

1.  **Wearable Device:** Flattens sensor data (HR, stress, activity) and transmits it to the child's mobile device. Uses TinyLSTM (TensorFlow Lite for Microcontrollers).
2.  **Child's Mobile Device:** Picks up environmental data, processes user input, and transmits all aggregated data to the cloud. Uses TinyLSTM (TensorFlow Lite).
3.  **Parent's Mobile Device:** Used for alerts, timers, and other real-time notifications. Uses TinyLSTM (TensorFlow Lite).