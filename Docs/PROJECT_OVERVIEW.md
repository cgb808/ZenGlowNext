## 1. Project Overview

**Project Name:** Wellness Prediction & Digital Companion Pipeline

**Mission:** To create a multi-tiered AI system that monitors a child's wellness through a wearable device, predicts future trends related to sleep and school stress, and provides actionable, empathetic insights to parents via a digital avatar named (enhanced)ZenMoonAvitar.

## 2. System Architecture Components

### A. Wearable Device

*   **Hardware:** Low-power microcontroller with HR, EDA, and accelerometer sensors.
*   **On-Device AI:** TinyLSTM (TF Lite Micro) for real-time data smoothing, anomaly detection, and sleep stage classification.
*   **Communication:** Bluetooth Low Energy (BLE).

### B. Child's Mobile Application

*   **Function:** Acts as a context hub and interactive front-end.
*   **Data Sources:** Aggregates data from the wearable, phone sensors (atmospheric), user interactions (games/feedback), and the school calendar.
*   **On-Device AI:** TinyLSTM for engagement analysis and classification of sleep/stress patterns correlated with school events.
*   **Communication:** HTTP/MQTT to the cloud backend.

### C. Cloud Backend (Flask API)

*   **Core Technology:** Python, Flask, Docker.
*   **Databases:**
    *   **Time-Series DB (TimescaleDB):** Stores numerical wellness metrics (stress, sleep_duration) and events.
    *   **Vector DB (Weaviate):** Stores contextual embeddings (BGE-Large) for semantic search.
*   **AI Models:**
    *   **Forecasting (Darts):** TFTModel for multi-variate prediction of stress and sleep.
    *   **Insight Generation (Gemma/Phi-3):** LLM to create natural language recommendations.
*   **Real-Time Communication:** WebSockets for push alerts to the parent app.

### D. Parent's Mobile Application

*   **Function:** Serves as the primary insight and empathy hub for the parent.
*   **Key Feature:** The (enhanced)ZenMoonAvitar, which visually represents the child's predicted emotional and physical state.
*   **On-Device AI:** TinyLSTM for intelligent, context-aware reminders and alerts based on cloud forecasts.

## 3. Key API Endpoints (Cloud Backend)

*   `POST /api/ingest`: Ingests data from the child's mobile app.
*   `GET /api/forecast/<child_id>`: Generates and returns future wellness forecasts.
*   `POST /api/insights`: Generates and returns actionable recommendations.
*   `WebSocket /api/alerts`: Pushes real-time alerts to the parent app.

## 4. Deployment & Operations

*   **Containerization:** Docker and docker-compose for creating a reproducible environment for the Flask app, TimescaleDB, and Weaviate.
*   **Web Server:** Gunicorn for running the Flask application in production.
*   **CI/CD:** Automated testing with pytest and deployment pipeline.
*   **Monitoring:** Logging, Prometheus for metrics, and Sentry for error tracking.

## 5. Security & Scalability

*   **Authentication:** Secure endpoints using JWT tokens.
*   **Rate Limiting:** Protect against abuse with request limits.
*   **Scalability:** Horizontally scale the Flask application workers using Docker.
*   **Infrastructure:** Use Nginx as a reverse proxy and HTTPS for secure communication.
