# Architecture Details (Flask Backend)

Audience: Backend Developers.

Purpose: A detailed technical guide to the Flask application's code, structure, models, and deployment.

## 1. Overview

This document details the Flask cloud backend, which serves as the central hub for ingesting data, running predictive models, and serving insights.

## 2. Core Setup & Dependencies

### Installation

```bash
pip install flask flask-cors flask-sqlalchemy psycopg2-binary weaviate-client darts[all] transformers torch sentence-transformers flask-socketio gunicorn
```

### Application Structure (app.py)

```python
import os
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
import weaviate
from darts.models import TFTModel
from darts import TimeSeries
from transformers import AutoModelForCausalLM, AutoTokenizer
from FlagEmbedding import BGEM3FlagModel
import logging

# Basic App Setup
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/wellness_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model placeholders (lazy-loaded)
bge_model = None
darts_model = None
llm_model = None
llm_tokenizer = None
vector_client = None
```

## 3. Database Models (SQLAlchemy for TimescaleDB)

The database stores child profiles and their continuous wellness metrics.

```python
class Child(db.Model):
    __tablename__ = 'children'
    id = db.Column(db.String(50), primary_key=True)
    age = db.Column(db.Integer)
    baseline_stress = db.Column(db.Float)
    school_events = db.Column(db.JSON)

class WellnessMetric(db.Model):
    __tablename__ = 'wellness_metrics'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    child_id = db.Column(db.String(50), db.ForeignKey('children.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    heart_rate = db.Column(db.Float)
    stress_level = db.Column(db.Float)
    activity_intensity = db.Column(db.Float)
    sleep_duration = db.Column(db.Float) # Cumulative seconds
    sleep_state = db.Column(db.String(20)) # e.g., 'light', 'deep', 'awake'
```

## 4. API Endpoints & Logic

### A. Data Ingestion & Embedding

This endpoint receives data, stores it in TimescaleDB, and triggers the embedding process for Weaviate.

```python
@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    data = request.json
    if not data or 'child_id' not in data:
        abort(400, description="Missing child_id in request body")

    try:
        # Store metric in TimescaleDB
        metric = WellnessMetric(
            child_id=data['child_id'],
            timestamp=datetime.fromtimestamp(data['timestamp']),
            heart_rate=data['wellness_metrics']['hr'],
            stress_level=data['wellness_metrics']['stress'],
            sleep_duration=data['wellness_metrics'].get('sleep_duration', 0),
            sleep_state=data['wellness_metrics'].get('sleep_state', 'awake')
        )
        db.session.add(metric)
        db.session.commit()

        # Asynchronously generate embeddings
        _generate_embeddings(data)

        return jsonify({"status": "success"}), 201

    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        db.session.rollback()
        abort(500, description="Failed to process request.")


def _generate_embeddings(data):
    # This should be run in a background task (e.g., Celery)
    global vector_client, bge_model
    if vector_client is None: # Lazy initialization
        vector_client = weaviate.Client("http://weaviate:8080")
    if bge_model is None:
        bge_model = BGEM3FlagModel("BAAI/bge-large-en-v1.5", use_fp16=True)

    # Create a rich text string for embedding
    context_text = (
        f"Child {data['child_id']} at age {data.get('context', {}).get('user_profile', {}).get('age')}: "
        f"Stress level was {data['wellness_metrics']['stress']:.2f}. "
        f"Sleep state was {data['wellness_metrics'].get('sleep_state')}. "
        f"School events: {data.get('context', {}).get('school_events', 'None')}. "
        f"Interaction: {data.get('interaction', {}).get('event', 'None')}."
    )

    embedding = bge_model.encode([context_text])[0]

    vector_client.data_object.create(
        data_object={
            "text": context_text,
            "child_id": data['child_id'],
            "timestamp": data['timestamp']
        },
        class_name="WellnessContext",
        vector=embedding.tolist()
    )
```

### B. Multi-Variate Forecasting with Darts

This endpoint uses the powerful TFTModel to forecast both stress and sleep, considering school events as a known future covariate.

```python
@app.route('/api/forecast/<child_id>', methods=['GET'])
def forecast(child_id):
    # This is a simplified example; in production, the model would be pre-trained nightly.
    global darts_model
    metrics = WellnessMetric.query.filter_by(child_id=child_id).order_by(WellnessMetric.timestamp).limit(200).all()
    if len(metrics) < 24: # Need enough data to forecast
        return jsonify({"error": "Not enough data for a forecast"}), 404

    df = pd.DataFrame([{'timestamp': m.timestamp, 'stress': m.stress_level, 'sleep_duration': m.sleep_duration/3600} for m in metrics])
    series = TimeSeries.from_dataframe(df, 'timestamp', ['stress', 'sleep_duration'], freq='H')

    if darts_model is None:
        darts_model = TFTModel(input_chunk_length=24, output_chunk_length=12, n_epochs=50) # Simplified training
        darts_model.fit(series, verbose=False) # In production, load a pre-trained model

    prediction = darts_model.predict(n=24)
    forecast_df = prediction.pd_dataframe()

    return jsonify({"forecast": forecast_df.to_dict('list')})
```

### C. Insight Generation and Real-Time Alerts

The /insights endpoint combines the forecast with retrieved context to generate a recommendation. The WebSocket pushes alerts based on these insights.

```python
@app.route('/api/insights', methods=['POST'])
def generate_insights():
    # ... (code to get forecast and retrieve context from Weaviate) ...

    prompt = f"""
    Context:
    - Forecast: Stress is predicted to be {forecast['stress_peak']:.2f}. Sleep may be disrupted.
    - Historical Context: {retrieved_context}

    Task: Generate a 2-sentence actionable recommendation for a parent of an 8-year-old child. Be empathetic and specific.
    """

    # ... (LLM generation logic) ...

    # Emit a real-time alert via WebSocket
    socketio.emit('alert', {'child_id': child_id, 'message': recommendation, 'type': 'proactive_tip'}, room=child_id)

    return jsonify({"recommendation": recommendation})

@socketio.on('subscribe')
def handle_subscribe(data):
    # A parent app subscribes to alerts for their child
    child_id = data['child_id']
    join_room(child_id)
    emit('message', {'data': f'Subscribed to alerts for {child_id}'})
```

## 5. Deployment (Docker & Gunicorn)

The docker-compose.yml file orchestrates the Flask app, TimescaleDB, and Weaviate services. Gunicorn is used as the production WSGI server for performance and concurrent request handling.

```yaml
version: '3.8'
services:
  flask_app:
    build: .
    ports: ['5000:5000']
    environment:
      - DATABASE_URL=postgresql://user:password@timescale:5432/wellness_db
    depends_on: [timescale, weaviate]
  timescale:
    image: timescale/timescaledb:latest-pg14
    # ... (environment and volumes)
  weaviate:
    image: semitechnologies/weaviate:1.23.0
    # ... (environment and volumes)
```

### Dockerfile

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

## 6. Testing and Performance

- Testing: Use pytest with an in-memory sqlite database for unit tests. Mock external services like Weaviate.
- Performance:
  - Model Caching: The lazy-loading pattern ensures large models are only loaded into memory once.
  - Asynchronous Tasks: Use a task queue like Celery to handle non-blocking operations like embedding generation.
  - Database Indexing: Ensure child_id and timestamp are indexed for fast queries.
