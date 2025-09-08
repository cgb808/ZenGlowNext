# AI Model Architecture for ZenGlow

This document outlines the three-tiered AI model architecture that powers the intelligent features in ZenGlow.

---

## Model 1: The Wearable Model (Pattern Recognition)

This is a tiny LSTM model designed to run on a wearable device. Its sole responsibility is to analyze raw sensor data in real-time.

-   **Function**: It acts as an intelligent pre-processor. It doesn't understand the *why* behind the data, it just recognizes the *what*.
-   **Input**: A continuous stream of accelerometer and heart rate data.
-   **Output**: Structured events, such as `{"event": "hr_spike", "value": 120}` or `{"event": "activity_change", "value": "walking"}`.
-   **Analogy**: This model is the sensory nerve. It feels the heat but does not decide to pull the hand away.

---

## Model 2: The Companion Behavior Model (Decision Making)

This is a small, on-device decision-making model that controls the `ZenGlowCompanion` component within the mobile app.

-   **Function**: It controls the UI/UX of the companion, deciding how it should act based on the user's interactions with the app.
-   **Input**: The app's UI context, such as `{"event": "user_scrolling", "active_screen": "dashboard"}`.
-   **Output**: A specific, predefined action for the companion to perform, such as `hide()` or `lookAt('metrics_card')`.
-   **Analogy**: This model is the reflex system. It controls the application's body language and immediate reactions.

---

## Model 3: Smollm2 (Reasoning & Conversation)

The `smollm2` model is a higher-level language model that does not operate in real-time. It analyzes the historical data collected by the other two models to provide deeper insights.

-   **Function**: It takes historical data and provides predictions, recommendations, and conversational insights for the parent or user.
-   **Input**: A summary of the day's events from both the wearable (e.g., "3 HR spikes today") and the companion (e.g., "Parent spent 5 minutes looking at the trends view").
-   **Output**: Natural language insights, such as, "It looks like Alex's heart rate often spikes around midday. This might be a good time to check in or suggest a calming activity."
-   **Analogy**: This model is the conscious brain. It analyzes past experiences to think, reason, and communicate.

---

## AI Agents & RAG Infrastructure

The ZenGlow AI ecosystem includes sophisticated AI agents that power data ingestion, processing, and insight generation through a hardened RAG (Retrieval-Augmented Generation) pipeline.

### Data Ingestion & Processing

- **Hardened RAG Pipeline**: Production-ready ingestion with async workflows, deduplication, rate limiting, and comprehensive validation
- **Vector Embeddings**: BGE-Large model for semantic search across wellness data
- **Real-time Processing**: Async queue-based processing with backpressure handling

### Security & Reliability

For production deployments, the AI agents implement enterprise-grade security patterns:

- **Rate Limiting**: Token bucket and sliding window algorithms
- **Input Validation**: Comprehensive schema validation and sanitization
- **Retry Mechanisms**: Exponential backoff with circuit breaker patterns
- **Monitoring**: Prometheus metrics and health checks

**📖 See the complete guide**: [RAG Ingestion Hardening Guide](../docs/rag/hardening.md)

---

This three-tiered system is highly efficient. Each model is specialized for its task, ensuring the app remains fast and responsive while delivering powerful, intelligent features.
